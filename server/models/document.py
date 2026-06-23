"""
知识文档模型
映射数据库表 t_document，存储上传的知识文档元信息
"""
from datetime import datetime
from ..extensions import db


class Document(db.Model):
    """知识文档模型类，对应t_document表"""

    __tablename__ = "t_document"

    # ==================== 表字段 ====================
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="文档ID")
    title = db.Column(db.String(200), nullable=False, comment="文档标题")
    content = db.Column(db.Text, comment="解析后的纯文本内容")
    file_name = db.Column(db.String(200), default=None, comment="原始文件名")
    file_type = db.Column(db.String(20), default=None, comment="文件类型：pdf/docx/txt/md")
    file_size = db.Column(db.Integer, default=0, comment="文件大小（字节）")
    topic = db.Column(db.String(50), default=None, comment="文档主题分类")
    chunk_count = db.Column(db.Integer, default=0, comment="文本分块数量")
    status = db.Column(db.SmallInteger, default=1, comment="状态：1正常 0已删除")
    uploader_id = db.Column(db.Integer, db.ForeignKey("t_user.id"), nullable=False, comment="上传者ID")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # ==================== 关联关系 ====================
    chunks = db.relationship("DocumentChunk", backref="document", lazy="dynamic",
                             cascade="all, delete-orphan")

    def to_dict(self, include_content=False):
        """
        将文档对象序列化为字典
        参数：
            include_content: 是否包含完整文本内容（列表页不需要）
        返回：dict
        """
        result = {
            "id": self.id,
            "title": self.title,
            "file_name": self.file_name or "",
            "file_type": self.file_type or "",
            "file_size": self.file_size,
            "topic": self.topic or "",
            "chunk_count": self.chunk_count,
            "status": self.status,
            "uploader_id": self.uploader_id,
            "uploader_name": self.uploader.username if self.uploader else "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }
        if include_content:
            result["content"] = self.content or ""
            # 取前200字符作为内容摘要
            result["content_preview"] = (self.content or "")[:200]
        return result

    def soft_delete(self):
        """
        软删除文档（将status置为0，不物理删除记录）
        """
        self.status = 0
        db.session.commit()

    def __repr__(self):
        return f"<Document {self.title}>"
