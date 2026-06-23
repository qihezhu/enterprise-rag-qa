"""
客户运营记录模型
审计打标签、群发任务等客户运营操作
"""
from ..extensions import db
from datetime import datetime


class CustomerRecord(db.Model):
    """客户运营记录表"""
    __tablename__ = "t_customer_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), nullable=False, comment="企微员工 UserID")
    external_userid = db.Column(db.String(64), nullable=False, comment="外部联系人 UserID")
    action_type = db.Column(
        db.Enum("tag", "broadcast", "follow"),
        nullable=False,
        comment="操作类型",
    )
    detail_json = db.Column(db.JSON, comment="操作详情 (JSON)")
    api_result = db.Column(db.JSON, comment="企微 API 返回结果")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        db.Index("idx_cr_user_id", "user_id"),
        db.Index("idx_cr_external_userid", "external_userid"),
        db.Index("idx_cr_action_type", "action_type"),
        db.Index("idx_cr_created_at", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "external_userid": self.external_userid,
            "action_type": self.action_type,
            "detail_json": self.detail_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
