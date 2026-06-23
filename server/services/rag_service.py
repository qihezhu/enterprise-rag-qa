"""
RAG（检索增强生成）核心服务模块
实现完整的RAG流水线：
文档加载 → 文本分割 → 向量化嵌入 → Chroma存储 → 相似度检索 → LLM生成回答
"""
import re
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .vector_store_service import VectorStoreService


class RAGService:
    """
    RAG核心服务类
    封装从文档处理到智能问答的完整流程
    """

    def __init__(self, config):
        """
        初始化RAG服务
        参数：
            config: Flask应用配置对象
        """
        # 初始化嵌入模型（用于将文本转为向量）
        self.embedding_model = OllamaEmbeddings(
            base_url=config["OLLAMA_BASE_URL"],
            model=config["EMBEDDING_MODEL_NAME"],
        )

        # 初始化大语言模型（用于生成回答）
        self.llm = ChatOllama(
            base_url=config["OLLAMA_BASE_URL"],
            model=config["LLM_MODEL_NAME"],
            temperature=0.3,  # 适度提高温度，让回答更自然充实
        )

        # 初始化文本分割器（将长文本切分为适合检索的小块）
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config["CHUNK_SIZE"],          # 每块500字符
            chunk_overlap=config["CHUNK_OVERLAP"],    # 相邻块重叠50字符
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],  # 中文友好的分割符优先级
        )

        # 初始化Chroma向量库服务
        self.vector_store = VectorStoreService(
            persist_directory=config["CHROMA_PERSIST_DIR"],
            embedding_function=self.embedding_model,
            collection_name=config["CHROMA_COLLECTION_NAME"],
        )

        self.top_k = config["TOP_K_RETRIEVAL"]
        self.relevance_threshold = 1.35  # 余弦距离阈值，超过此值视为不相关

    # ==================== 文档处理流程 ====================

    def split_documents(self, documents):
        """
        将LangChain Document列表分割为固定大小的文本块
        参数：
            documents: LangChain Document对象列表（由DocumentLoader加载）
        返回：
            分割后的Document块列表
        """
        chunks = self.text_splitter.split_documents(documents)
        return chunks

    def add_to_vector_store(self, chunks, document_id, file_name, topic=None):
        """
        将文档块向量化并存入Chroma向量库
        参数：
            chunks: 分割后的Document块列表
            document_id: 文档在MySQL中的ID
            file_name: 原始文件名（用于回答中标注来源）
            topic: 文档主题分类（可选）
        返回：
            (成功添加的块数量, 向量ID列表)
        """
        if not chunks:
            return 0, []

        # 为每个块生成唯一ID并添加metadata
        ids = []
        for i, chunk in enumerate(chunks):
            vector_id = f"doc_{document_id}_chunk_{i}"
            ids.append(vector_id)
            # 在metadata中记录文档ID和文件名，便于检索时溯源和删除时定位
            chunk.metadata["document_id"] = document_id
            chunk.metadata["file_name"] = file_name
            if topic:
                chunk.metadata["topic"] = topic

        # 批量添加到Chroma（自动调用嵌入模型进行向量化）
        print(f"[RAG入库] 准备添加{len(chunks)}个文档块到Chroma，topic={topic}, collection={self.vector_store.collection_name}")
        self.vector_store.add_documents(chunks, ids)
        print(f"[RAG入库] 添加完成")
        # 验证是否持久化成功
        stats = self.get_vector_store_stats()
        print(f"[RAG入库] 向量库当前总数: {stats['count']}")
        return len(chunks), ids

    def delete_from_vector_store(self, document_id):
        """
        从向量库中删除指定文档的所有向量
        参数：
            document_id: 文档ID
        """
        self.vector_store.delete_by_document_id(document_id)

    # ==================== 检索与生成流程 ====================

    def retrieve(self, query, topic=None):
        """
        根据用户问题检索最相关的知识库内容，并过滤低相关度结果
        使用关键词加权重排序提升检索准确率
        """
        stats = self.get_vector_store_stats()
        filter_dict = {"topic": topic} if topic else None
        print(f"[RAG检索] 向量库当前总数: {stats['count']}, 查询: {query[:60]}, topic: {topic or '全部'}")
        # 检索更多候选（3倍top_k），为关键词重排序留空间
        raw_results = self.vector_store.search(query, top_k=self.top_k * 3, filter=filter_dict)
        print(f"[RAG检索] 原始返回{len(raw_results)}条结果")

        # 提取查询关键词 — 双字滑动窗口 + 完整词提取
        stop_words = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
                      '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
                      '自己', '这', '怎么', '什么', '如何', '怎样', '哪些', '哪', '吗', '呢', '吧', '啊',
                      '可以', '需要', '应该', '能', '能够', '还是', '或者', '以及', '得', '地',
                      '怎么走', '是什么', '怎么样', '如何做', '怎么做', '如何走', '关于'}
        # 完整词提取（去掉停用词和疑问后缀）
        raw_words = [w for w in re.findall(r'[一-鿿\w]+', query) if w not in stop_words and len(w) >= 2]
        # 双字滑动窗口提取（覆盖复合词被整段匹配漏掉的情况）
        bigrams = set()
        for w in raw_words:
            for i in range(len(w) - 1):
                bg = w[i:i+2]
                if bg not in stop_words:
                    bigrams.add(bg)
        query_kw = list(bigrams | set(raw_words))
        # 按长度降序排列（长词优先匹配，更精确）
        query_kw.sort(key=lambda x: -len(x))

        # 关键词加权重排序
        def keyword_bonus(doc):
            if not query_kw:
                return 0.0
            content = doc.page_content
            hit_count = sum(1 for kw in query_kw if kw in content)
            # 每个命中关键词降低分数0.05（余弦距离越低越好）
            return hit_count * 0.05

        # 按调整后分数排序
        scored_results = [(doc, float(s) - keyword_bonus(doc)) for doc, s in raw_results]
        scored_results.sort(key=lambda x: x[1])

        for i, (doc, score) in enumerate(scored_results):
            preview = doc.page_content[:80].replace('\n', ' ')
            passed = "PASS" if score < self.relevance_threshold else "DROP"
            kw_hits = sum(1 for kw in query_kw if kw in doc.page_content) if query_kw else 0
            print(f"  #{i+1} {passed} 距离:{round(score,4)} kw_hits:{kw_hits} 来源:{doc.metadata.get('file_name','?')} 内容:{preview}...")

        # 过滤低相关度结果
        relevant = [(doc, score) for doc, score in scored_results if score < self.relevance_threshold]
        relevant = relevant[:self.top_k]
        print(f"[RAG检索] 过滤后保留{len(relevant)}条高相关结果")
        return relevant

    def generate_answer(self, query, retrieved_docs):
        """
        基于检索到的知识库内容，调用LLM生成回答
        参数：
            query: 用户问题
            retrieved_docs: 检索到的相关文档块列表 [(Document, score), ...]
        返回：
            {"answer": "回答文本", "sources": [来源信息列表]}
        """
        if not retrieved_docs:
            return {
                "answer": "抱歉，我在知识库中没有找到与您问题相关的信息。请尝试换个方式提问，或者联系管理员补充相关知识文档。",
                "sources": [],
            }

        # 去重：移除内容高度相似的文本块（重叠度>60%视为重复）
        deduped_docs = []
        for doc, score in retrieved_docs:
            is_dup = False
            for existing_doc, _ in deduped_docs:
                if self._content_overlap(doc.page_content, existing_doc.page_content) > 0.6:
                    is_dup = True
                    break
            if not is_dup:
                deduped_docs.append((doc, score))

        # 拼接去重后的文档块作为上下文
        context_parts = []
        for doc, _score in deduped_docs:
            file_name = doc.metadata.get("file_name", "未知来源")
            context_parts.append(f"【文档：{file_name}】\n{doc.page_content}")

        context = "\n\n---\n\n".join(context_parts)

        # 构建Prompt模板 — 生成详细有条理的回答，类似人工客服风格
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是企业知识库内部助手，根据企业知识库中的文档内容回答员工问题。

回答规则：
1. 以【知识库内容】为唯一依据，可以归纳总结但严禁编造具体的条款、数字、日期
2. 将知识库中的信息组织成清晰的要点，每个要点独占一行
3. 如果有流程步骤，按顺序用"1. 2. 3."编号列出
4. 回答末尾单独一行写"来源：文档名称"，文档名称必须从【知识库内容】中的"【文档：xxx】"标记中原样复制，严禁修改或编造
5. 使用纯文本，禁止任何Markdown格式符号（** ## - * ` ![] ）
6. 禁止引用或提及图片、图像、截图
7. 禁止生成"看起来我错误地尝试引用了一张图片"等自我纠正文字
8. 禁止猜测知识库中有哪些文档或没有哪些文档，只基于当前提供的文档内容回答
9. 如果当前提供的知识库内容不足以回答问题，回复"根据现有知识库资料，暂时无法回答您的问题，建议联系相关部门获取最新信息"

【知识库内容】
{context}"""),
            ("human", "{question}"),
        ])

        # 使用LCEL链式调用
        chain = prompt | self.llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": query})

        # 后处理：去除LLM可能仍然输出的Markdown格式符号
        answer = self._strip_markdown(answer)

        # 提取来源信息
        sources = []
        for doc, score in retrieved_docs:
            sources.append({
                "file_name": doc.metadata.get("file_name", ""),
                "chunk_index": doc.metadata.get("chunk_index", 0),
                "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content,
                "relevance_score": round(float(score), 4) if score else 0,
            })

        return {
            "answer": answer,
            "sources": sources,
        }

    @staticmethod
    def _content_overlap(text1, text2):
        """
        计算两段文本的内容重叠度（用于去重）
        使用字符级Jaccard相似度，重叠度>60%视为重复内容
        """
        if not text1 or not text2:
            return 0
        set1 = set(text1)
        set2 = set(text2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0

    @staticmethod
    def _strip_markdown(text):
        """
        去除文本中的Markdown格式符号，保留编号列表格式
        """
        # 去除粗体 **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        # 去除斜体 *text*
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
        # 去除行内代码 `text`
        text = re.sub(r'`(.+?)`', r'\1', text)
        # 去除标题 # ## ### 等
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # 去除无序列表 - 或 * 开头（但不影响编号列表）
        text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
        # 保留编号列表 "1. " "2. " — 这是纯文本兼容的格式
        return text

    def ask(self, query, topic=None):
        """
        对外暴露的完整问答接口（一站式：检索 + 生成）
        参数：
            query: 用户问题字符串
            topic: 可选的主题过滤
        返回：
            {"answer": "回答", "sources": [来源列表]}
        """
        # 步骤1：检索相关文档（可选按主题过滤）
        retrieved_docs = self.retrieve(query, topic=topic)
        # 步骤2：基于检索结果生成回答
        result = self.generate_answer(query, retrieved_docs)
        return result

    def get_vector_store_stats(self):
        """
        获取向量库统计信息
        返回：dict
        """
        return self.vector_store.get_collection_stats()
