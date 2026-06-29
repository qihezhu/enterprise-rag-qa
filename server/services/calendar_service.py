"""
日程自动驾驶服务
自然语言查忙闲、预约会议、修改日程，强制 timezone=Asia/Shanghai
"""
from datetime import datetime, timedelta, timezone
from flask import current_app
from ..clients.wecom_client import wecom_client
from .contact_service import contact_service

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
            current_app.logger.error(f"[忙闲] check_schedule 失败: {resp}")
            return {"errcode": resp.get("errcode"), "errmsg": resp.get("errmsg", "查询失败"), "busy_slots": [], "free_slots": []}
        except Exception as e:
            current_app.logger.exception(f"[忙闲] check_schedule 异常: {e}")
            return {"errcode": -1, "errmsg": f"企微API异常: {e}", "busy_slots": [], "free_slots": []}

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

        # ---- 名称 → userid 解析（百炼传中文名，企微 API 要 userid） ----
        resolved_organizer = self._resolve_userid(organizer)
        if not resolved_organizer:
            return {"errcode": -1, "errmsg": f"组织者解析失败: {organizer!r} 不在通讯录中，无法预约"}
        organizer = resolved_organizer  # 后续全部使用 userid

        if isinstance(attendees, list):
            resolved_attendees = []
            for a in attendees:
                r = self._resolve_userid(a)
                if r:
                    resolved_attendees.append(r)
                else:
                    current_app.logger.warning(f"[日程] 参会人解析失败: {a!r}，已跳过该成员")
            attendees = resolved_attendees
        elif attendees:
            r = self._resolve_userid(attendees)
            attendees = [r] if r else []
        else:
            attendees = []
        # ---- 解析结束 ----

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
                schedule_id = resp.get("schedule_id", "")
                # 新增：主动给每个参会人发应用消息邀请（oa/schedule/add 不会自动发邀请）
                self._send_meeting_invites(all_attendees, organizer, subject, start_dt, end_dt, room, schedule_id)
                return {
                    "schedule_id": schedule_id,
                    "subject": subject,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "attendees": all_attendees,
                    "organizer": organizer,
                }
            current_app.logger.error(f"[日程] add_schedule 失败: {resp}")
            return {"errcode": resp.get("errcode"), "errmsg": resp.get("errmsg", "创建失败")}
        except Exception as e:
            current_app.logger.exception(f"[日程] add_schedule 异常: {e}")
            return {"errcode": -1, "errmsg": f"企微API异常: {e}"}

    def _send_meeting_invites(self, all_attendees, organizer, subject, start_dt, end_dt, room, schedule_id):
        """给每个参会人发送会议邀请应用消息（不含 organizer）
        不阻塞主流程：发送失败仅写日志，不影响日程创建结果。
        """
        invite_text = (
            f"📅 会议邀请\n"
            f"主题：{subject}\n"
            f"时间：{start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}\n"
            f"地点：{room or '无指定地点'}\n"
            f"组织者：{organizer}\n"
            f"日程ID：{schedule_id}\n\n"
            f"请准时参会。"
        )
        for uid in all_attendees:
            if uid == organizer:  # 跳过组织者
                continue
            try:
                wecom_client.send_message(uid, "text", invite_text)
                current_app.logger.info(f"[日程邀请] 已发送 uid={uid} subject={subject}")
            except Exception as e:
                current_app.logger.warning(f"[日程邀请] 发送失败 uid={uid} err={e}")

    def get_calendar(self, user_id=None):
        """获取日历"""
        try:
            resp = wecom_client.get_calendar()
            if resp.get("errcode") == 0:
                return {"calendar_list": resp.get("calendar_list", [])}
            current_app.logger.error(f"[日历] get_calendar 失败: {resp}")
            return {"errcode": resp.get("errcode"), "errmsg": resp.get("errmsg", "获取失败"), "calendar_list": []}
        except Exception as e:
            current_app.logger.exception(f"[日历] get_calendar 异常: {e}")
            return {"errcode": -1, "errmsg": f"企微API异常: {e}", "calendar_list": []}

    # ==================== 时间工具 ====================

    def _resolve_userid(self, name):
        """将 organizer / attendees 中的名称解析为企微 userid
        - 纯英文/数字（看起来是 userid）→ 直接返回
        - 含中文 → 调用 contact_service.search_user() 查通讯录
        - 解析失败 → 返回 None（调用方决定如何降级）
        不修改 contact_service.py，不影响查通讯录功能。
        """
        if not name:
            return None
        name = str(name).strip()
        if not name:
            return None
        # 纯英文/数字/下划线 → 当 userid 直接返回（避免无谓的企微 API 调用）
        if not any('\u4e00' <= c <= '\u9fff' for c in name):
            return name
        # 含中文 → 调通讯录搜索（search_user 已带缓存/拼音/部门遍历兜底）
        try:
            result = contact_service.search_user(name)
            users = result.get("results", []) if isinstance(result, dict) else []
            if users:
                resolved = users[0].get("userid", "")
                if resolved:
                    current_app.logger.info(f"[日程] 名称解析: {name!r} → userid={resolved!r}")
                    return resolved
        except Exception as e:
            current_app.logger.warning(f"[日程] 名称解析异常 name={name!r} err={e}")
        return None

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
