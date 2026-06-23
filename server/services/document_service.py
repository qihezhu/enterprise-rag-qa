"""
文档解析服务模块
支持PDF、DOCX、TXT、Markdown等格式的文件解析，将文件内容提取为纯文本
"""
import os
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document


class DocumentService:
    """
    文档解析服务类
    根据文件类型选择合适的LangChain加载器，将文件解析为纯文本
    TXT/MD文件使用TextLoader直接读取，PDF使用PyPDFLoader，DOCX使用Docx2txtLoader
    """

    @classmethod
    def parse(cls, file_path, file_type):
        """
        解析文档文件，提取纯文本内容
        参数：
            file_path: 文件的绝对路径
            file_type: 文件扩展名（不含点号），如 'pdf', 'docx', 'txt', 'md'
        返回：
            {
                "content": "完整纯文本字符串",
                "documents": [LangChain Document对象列表]
            }
        异常：
            ValueError: 不支持的文件类型
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_type = file_type.lower()

        if file_type in ("txt", "md"):
            # TXT和MD都是纯文本文件，直接读取
            documents = cls._load_text(file_path)
        elif file_type == "pdf":
            loader = PyPDFLoader(file_path)
            documents = loader.load()
        elif file_type == "docx":
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
        else:
            raise ValueError(f"不支持的文件类型: {file_type}，支持的类型: pdf, docx, txt, md")

        # 拼接所有页/段落的文本
        full_text = "\n\n".join([doc.page_content for doc in documents])

        return {
            "content": full_text,
            "documents": documents,
        }

    @classmethod
    def _load_text(cls, file_path):
        """
        读取纯文本文件（TXT/MD），自动尝试多种编码
        参数：
            file_path: 文件路径
        返回：
            LangChain Document对象列表
        """
        # 尝试常见编码
        for encoding in ("utf-8", "gbk", "gb2312", "utf-8-sig"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                return [Document(page_content=content, metadata={"source": file_path})]
            except UnicodeDecodeError:
                continue

        # 所有编码都失败时，使用errors='ignore'兜底
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path})]

    @classmethod
    def get_supported_types(cls):
        """
        获取支持的文件类型列表
        返回：list[str]
        """
        return ["pdf", "docx", "txt", "md"]
