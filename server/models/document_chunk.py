"""
文档分块模型
映射数据库表 t_document_chunk，记录文档分块与Chroma向量库的映射关系
"""
from datetime import datetime
from ..extensions import db


class DocumentChunk(db.Model):
    """文档分块模型类，对应t_document_chunk表"""

    __tablename__ = "t_document_chunk"

    # ==================== 表字段 ====================
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="分块ID")
    document_id = db.Column(db.Integer, db.ForeignKey("t_document.id"), nullable=False, comment="所属文档ID")
    chunk_index = db.Column(db.Integer, nullable=False, comment="块序号（从0开始）")
    content = db.Column(db.Text, nullable=False, comment="块文本内容")
    vector_id = db.Column(db.String(100), default=None, comment="Chroma向量库中的向量唯一ID")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        """
        将分块对象序列化为字典
        返回：dict
        """
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content_preview": self.content[:100] if self.content else "",
            "vector_id": self.vector_id or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
