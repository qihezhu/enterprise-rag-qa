"""
日程记录模型
审计 AI Agent 创建的每一次会议/日程
"""
from ..extensions import db
from datetime import datetime


class ScheduleRecord(db.Model):
    """日程记录表"""
    __tablename__ = "t_schedule_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    organizer_user_id = db.Column(db.String(64), nullable=False, comment="组织者企微 UserID")
    schedule_id = db.Column(db.String(64), comment="企微日程 ID")
    subject = db.Column(db.String(200), nullable=False, comment="会议主题")
    start_time = db.Column(db.DateTime, comment="开始时间 (UTC)")
    end_time = db.Column(db.DateTime, comment="结束时间 (UTC)")
    attendees_json = db.Column(db.JSON, comment="参会人员列表 (JSON)")
    location = db.Column(db.String(200), comment="会议室/地点")
    status = db.Column(
        db.Enum("created", "updated", "cancelled"),
        default="created",
        comment="日程状态",
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间",
    )

    __table_args__ = (
        db.Index("idx_sr_organizer", "organizer_user_id"),
        db.Index("idx_sr_schedule_id", "schedule_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "organizer_user_id": self.organizer_user_id,
            "schedule_id": self.schedule_id,
            "subject": self.subject,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "attendees_json": self.attendees_json,
            "location": self.location,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
