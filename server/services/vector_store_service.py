"""
Chroma向量库操作服务模块
封装Chroma向量数据库的增删查操作，管理文档块向量的持久化存储
"""
import os
import chromadb
from langchain_chroma import Chroma


class VectorStoreService:
    """
    Chroma向量库操作封装类
    负责向量库的初始化、文档添加、相似度搜索和删除操作
    Chroma数据持久化到本地磁盘目录
    """

    def __init__(self, persist_directory, embedding_function, collection_name="knowledge_base"):
        """
        初始化向量库服务
        参数：
            persist_directory: Chroma数据持久化目录路径
            embedding_function: LangChain嵌入模型实例（用于文本向量化）
            collection_name: 向量集合名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # 确保持久化目录存在
        os.makedirs(persist_directory, exist_ok=True)

        # 使用 chromadb.PersistentClient 确保数据可靠持久化到磁盘
        chroma_client = chromadb.PersistentClient(path=persist_directory)

        self.store = Chroma(
            client=chroma_client,
            embedding_function=embedding_function,
            collection_name=collection_name,
        )

    def add_documents(self, chunks, doc_ids):
        """
        将文档块添加到向量库
        参数：
            chunks: LangChain Document对象列表（每个包含page_content和metadata）
            doc_ids: 与chunks对应的向量ID列表，格式：["doc_1_chunk_0", "doc_1_chunk_1", ...]
        返回：
            添加成功的向量数量
        """
        if not chunks:
            return 0
        print(f"[Chroma] 开始添加{len(chunks)}个文档块，第一个ID: {doc_ids[0] if doc_ids else 'N/A'}")
        self.store.add_documents(documents=chunks, ids=doc_ids)
        print(f"[Chroma] add_documents调用完成")
        # 立即验证
        col = self.store._collection
        print(f"[Chroma] 集合当前文档数: {col.count()}")
        return len(chunks)

    def search(self, query, top_k=4, filter=None):
        """
        相似度搜索：根据查询文本检索最相关的文档块
        参数：
            query: 查询文本字符串
            top_k: 返回的最相关结果数量
            filter: Chroma metadata过滤条件，如 {"topic": "财务管理"}
        返回：
            [(Document, score), ...] 按相似度降序排列的元组列表
        """
        col = self.store._collection
        filter_info = f", filter={filter}" if filter else ""
        print(f"[Chroma检索] 集合'{col.name}'当前有{col.count()}条向量，查询top_{top_k}{filter_info}: {query[:50]}")
        results = self.store.similarity_search_with_score(query, k=top_k, filter=filter)
        print(f"[Chroma检索] 返回{len(results)}条结果")
        return results

    def delete_by_document_id(self, document_id):
        """
        按文档ID删除向量库中该文档的所有向量块
        参数：
            document_id: 文档在MySQL中的ID
        返回：
            删除的向量数量
        """
        try:
            # 通过Chroma的metadata过滤删除
            self.store.delete(where={"document_id": str(document_id)})
            return True
        except Exception:
            return False

    def get_collection_stats(self):
        """
        获取向量库统计信息
        返回：
            {"count": 向量总数, "name": 集合名称}
        """
        try:
            collection = self.store._collection
            return {
                "count": collection.count(),
                "name": collection.name,
            }
        except Exception:
            return {"count": 0, "name": self.collection_name}
