"""
日程 Tool 端点（千问Agent平台调用）
提供忙闲查询、预约会议功能
"""
from flask import Blueprint, request, current_app
from ...services.calendar_service import calendar_service
from ...models.schedule_record import ScheduleRecord
from ...middleware.auth_middleware import require_tool_api_key
from ...utils.helpers import success_response, error_response, clean_tool_inputs
from ...extensions import db

# 注册到已有的 tool_bp
from .approval_tool import tool_bp


@tool_bp.route("/calendar/check-busy", methods=["POST"])
@require_tool_api_key
def check_busy():
    """
    查询用户忙闲状态
    输入: {"user_ids": ["zhangsan", "lisi"], "start_time": "2026-06-17T09:00:00", "end_time": "2026-06-17T18:00:00"}
    输出: {"busy_slots": [...], "free_slots": [...]}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    user_ids = data.get("user_ids", [])
    start_time = data.get("start_time", "")
    end_time = data.get("end_time", "")

    if not user_ids:
        return error_response("缺少 user_ids 参数", 400)
    if not start_time or not end_time:
        return error_response("缺少时间参数", 400)

    result = calendar_service.check_busy(user_ids, start_time, end_time)
    if "errcode" in result:
        return error_response(result.get("errmsg", "查询失败"), 500)
    return success_response(result, "查询完成")


@tool_bp.route("/calendar/book", methods=["POST"])
@require_tool_api_key
def book_meeting():
    """
    预约会议
    输入: {"organizer": "zhangsan", "attendees": ["lisi"], "subject": "周会", "start_time": "...", "end_time": "...", "room": "A301"}
    输出: {"schedule_id": "...", "status": "created"}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    organizer = data.get("organizer", "")
    attendees = data.get("attendees", [])
    subject = data.get("subject", "")
    start_time = data.get("start_time", "")
    end_time = data.get("end_time", "")
    room = data.get("room", "")

    if not organizer or not subject:
        return error_response("缺少必填参数: organizer 或 subject", 400)

    result = calendar_service.book_meeting(
        organizer, attendees, subject, start_time, end_time, room
    )
    if result.get("errcode", 0) != 0:
        return error_response(f"{result.get('errmsg')} [v3 start={start_time!r} end={end_time!r}]", 500)

    # 记录到数据库
    record = ScheduleRecord(
        organizer_user_id=organizer,
        schedule_id=result.get("schedule_id", ""),
        subject=subject,
        start_time=start_time if isinstance(start_time, str) else None,
        end_time=end_time if isinstance(end_time, str) else None,
        attendees_json=attendees,
        location=room or "",
        status="created",
    )
    db.session.add(record)
    db.session.commit()

    result["record_id"] = record.id
    return success_response(result, "会议预约成功")


@tool_bp.route("/calendar/get", methods=["POST"])
@require_tool_api_key
def get_calendar():
    """
    获取日历（获取 calendar_id）
    输入: {"user_id": "zhangsan"}  (可选)
    输出: {"calendar_list": [...]}
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "")
    result = calendar_service.get_calendar(user_id)
    if "errcode" in result:
        return error_response(result.get("errmsg", "获取失败"), 500)
    return success_response(result, "获取完成")
