"""
对话记录模型
映射数据库表 t_conversation，存储用户与知识库问答助手的对话历史
"""
from datetime import datetime
from ..extensions import db


class Conversation(db.Model):
    """对话记录模型类，对应t_conversation表"""

    __tablename__ = "t_conversation"

    # ==================== 表字段 ====================
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="对话ID")
    user_id = db.Column(db.Integer, db.ForeignKey("t_user.id"), nullable=False, comment="提问用户ID")
    question = db.Column(db.Text, nullable=False, comment="用户问题")
    answer = db.Column(db.Text, default=None, comment="模型回答")
    sources = db.Column(db.JSON, default=None, comment="参考来源列表JSON")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    def to_dict(self):
        """
        将对话记录序列化为字典
        返回：dict
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "",
            "question": self.question,
            "answer": self.answer or "",
            "sources": self.sources or [],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<Conversation {self.id}>"
