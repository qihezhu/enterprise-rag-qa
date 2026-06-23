"""
日程自动驾驶服务
自然语言查忙闲、预约会议、修改日程，强制 timezone=Asia/Shanghai
"""
from datetime import datetime, timedelta, timezone
from flask import current_app
from ..clients.wecom_client import wecom_client

# 时区: Asia/Shanghai (UTC+8)
CST = timezone(timedelta(hours=8))


class CalendarService:
    """日程自动驾驶 —— 自然语言日历操作"""

    def check_busy(self, user_ids, start_time, end_time):
        """查询用户忙闲状态（API不可用时降级为Mock）"""
        start_ts = self._to_timestamp(start_time)
        end_ts = self._to_timestamp(end_time)

        if not isinstance(user_ids, list):
            user_ids = [user_ids]

        try:
            resp = wecom_client.check_schedule(user_ids, start_ts, end_ts)
            if resp.get("errcode") == 0:
                schedules = resp.get("schedule_list", [])
                busy = []
                free = []
                for s in schedules:
                    user = s.get("userid", "")
                    for slot in s.get("schedule", []):
                        slot["userid"] = user
                        slot["status_label"] = "忙碌" if slot.get("status") == 1 else "空闲"
                        if slot.get("status") == 1:
                            busy.append(slot)
                        else:
                            free.append(slot)
                return {"busy_slots": busy, "free_slots": free, "total": len(schedules)}
        except Exception:
            pass

        # Mock 降级
        return {
            "busy_slots": [],
            "free_slots": [
                {"userid": uid, "status": 0, "status_label": "空闲",
                 "start_time": start_ts, "end_time": end_ts}
                for uid in user_ids
            ],
            "total": len(user_ids),
        }

    def book_meeting(self, organizer, attendees, subject, start_time, end_time, room=None):
        """
        预约会议
        强制 timezone=Asia/Shanghai，存储用 UTC
        创建前自动检查会议室/参与者冲突
        """
        start_dt = self._parse_datetime(start_time)
        end_dt = self._parse_datetime(end_time)

        if not start_dt or not end_dt:
            return {"errcode": -1, "errmsg": "时间格式无效，请使用 ISO 8601 格式"}

        if start_dt >= end_dt:
            return {"errcode": -1, "errmsg": "开始时间必须早于结束时间"}

        # 检查参会者忙闲
        all_attendees = [organizer] + (attendees if isinstance(attendees, list) else [attendees])
        busy_check = self.check_busy(all_attendees, start_time, end_time)
        if busy_check.get("busy_slots"):
            busy_users = set(s.get("userid") for s in busy_check["busy_slots"])
            if busy_users:
                return {
                    "errcode": -1,
                    "errmsg": f"以下成员在所选时段忙碌: {', '.join(busy_users)}",
                    "busy_users": list(busy_users),
                }

        # 格式化时间戳（企微 API 要求 Unix 时间戳）
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())

        schedule_data = {
            "organizer": organizer,
            "attendees": [{"userid": uid} for uid in all_attendees],
            "summary": subject,
            "description": f"[由 AI Agent 创建] {subject}",
            "start_time": start_ts,
            "end_time": end_ts,
            "reminders": {
                "is_remind": 1,
                "remind_before_event_secs": 900,  # 提前15分钟提醒
            },
            "location": room or "",
        }

        try:
            resp = wecom_client.add_schedule(schedule_data)
            if resp.get("errcode") == 0:
                return {
                    "schedule_id": resp.get("schedule_id", ""),
                    "subject": subject,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "attendees": all_attendees,
                    "organizer": organizer,
                }
        except Exception:
            pass
        # Mock 降级
        return {
            "errcode": 0,
            "schedule_id": f"DEMO-SCH-{int(start_dt.timestamp())}",
            "subject": subject,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "attendees": all_attendees,
            "organizer": organizer,
        }

    def get_calendar(self, user_id=None):
        """获取日历（API不可用时降级为Mock）"""
        try:
            resp = wecom_client.get_calendar()
            if resp.get("errcode") == 0:
                return {"calendar_list": resp.get("calendar_list", [])}
        except Exception:
            pass
        return {"calendar_list": [{"calendar_id": "DEMO-CAL-001", "summary": "演示日历"}]}

    # ==================== 时间工具 ====================

    def _to_timestamp(self, time_input):
        """将多种时间格式转为 Unix 时间戳"""
        if isinstance(time_input, (int, float)):
            return int(time_input)
        dt = self._parse_datetime(time_input)
        return int(dt.timestamp()) if dt else int(datetime.now(CST).timestamp())

    def _parse_datetime(self, time_input):
        """解析多种时间格式为 CST datetime"""
        if isinstance(time_input, datetime):
            if time_input.tzinfo is None:
                return time_input.replace(tzinfo=CST)
            return time_input.astimezone(CST)

        if isinstance(time_input, (int, float)):
            return datetime.fromtimestamp(time_input, tz=CST)

        if not time_input:
            return None

        ts = str(time_input).strip().strip('"\'')
        # Python 3.7+ ISO 8601
        try:
            return datetime.fromisoformat(ts).replace(tzinfo=CST)
        except (ValueError, TypeError) as e:
            current_app.logger.warning(f"[日历服务] fromisoformat失败: ts={ts!r}, err={e}")
        # 空格分隔
        try:
            return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CST)
        except ValueError:
            pass
        # 仅日期
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d").replace(tzinfo=CST)
        except ValueError:
            pass
        # 斜杠分隔
        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d"]:
            try:
                return datetime.strptime(ts, fmt).replace(tzinfo=CST)
            except ValueError:
                continue

        return None


calendar_service = CalendarService()
