"""
系统日志模型
映射数据库表 t_system_log，记录系统操作日志（登录、上传、问答等）
"""
from datetime import datetime
from ..extensions import db


class SystemLog(db.Model):
    """系统日志模型类，对应t_system_log表"""

    __tablename__ = "t_system_log"

    # ==================== 表字段 ====================
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = db.Column(db.Integer, db.ForeignKey("t_user.id"), default=None, comment="操作人ID")
    action = db.Column(db.String(50), nullable=False, comment="操作类型：LOGIN/DOC_UPLOAD/QA_ASK等")
    description = db.Column(db.String(500), default=None, comment="操作详细描述")
    ip_address = db.Column(db.String(50), default=None, comment="客户端IP地址")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")

    # ==================== 关联关系 ====================
    user = db.relationship("User", backref="logs")

    def to_dict(self):
        """
        将日志对象序列化为字典
        返回：dict
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.user.username if self.user else "匿名",
            "action": self.action,
            "description": self.description or "",
            "ip_address": self.ip_address or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self):
        return f"<SystemLog {self.action}>"
