"""
审批记录模型
审计企业微信对话式审批的每一次提交，用于管理端查询和回调状态同步
"""
from ..extensions import db
from datetime import datetime


class ApprovalRecord(db.Model):
    """审批记录表"""
    __tablename__ = "t_approval_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(64), nullable=False, comment="企微 UserID (申请人)")
    sp_no = db.Column(db.String(64), comment="企微审批单号")
    template_name = db.Column(db.String(100), nullable=False, comment="审批模板名称")
    status = db.Column(
        db.Enum("pending", "approved", "rejected", "cancelled"),
        default="pending",
        comment="审批状态",
    )
    fields_json = db.Column(db.JSON, comment="审批字段快照 (JSON)")
    card_msg_id = db.Column(db.String(64), comment="卡片消息ID (用于更新按钮)")
    response_code = db.Column(db.String(64), comment="卡片响应码 (用于 update_button)")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    __table_args__ = (
        db.Index("idx_ar_user_id", "user_id"),
        db.Index("idx_ar_sp_no", "sp_no"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sp_no": self.sp_no,
            "template_name": self.template_name,
            "status": self.status,
            "fields_json": self.fields_json,
            "card_msg_id": self.card_msg_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
