"""
企业微信回调 Blueprint
处理 URL 验证（GET）和事件推送（POST）+ 管理端状态查询
"""
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, current_app
from ..clients.crypto import verify_signature, verify_message_signature, decrypt_message
from ..clients.wecom_client import wecom_client
from ..services.event_service import event_service
from ..middleware.auth_middleware import login_required, admin_required
from ..utils.helpers import success_response, error_response, paginated_response
from ..extensions import redis_client

def _redis_ok():
    try:
        return redis_client is not None and redis_client.ping()
    except Exception:
        return False

wecom_bp = Blueprint("wecom", __name__, url_prefix="/api/wecom")

# 异步执行器，避免阻塞回调响应（企微要求 5 秒内响应）
_executor = ThreadPoolExecutor(max_workers=4)


@wecom_bp.route("/status", methods=["GET"])
@login_required
@admin_required
def status():
    """获取企微连接状态（管理端）"""
    redis_ok = False
    try:
        redis_ok = _redis_ok()
    except Exception:
        pass
    return success_response({
        "corp_id": current_app.config["WECOM_CORP_ID"] or "",
        "agent_id": current_app.config["WECOM_AGENT_ID"] or "",
        "secret_configured": bool(current_app.config["WECOM_SECRET"]),
        "callback_url": f"{request.host_url.rstrip('/')}/api/wecom/callback",
        "token_valid": False,
        "redis_ok": redis_ok,
    })


@wecom_bp.route("/test-token", methods=["POST"])
@login_required
@admin_required
def test_token():
    """测试 Token 获取（管理端）"""
    try:
        token = wecom_client.get_access_token()
        masked = f"{token[:8]}...{token[-8:]}" if len(token) > 20 else "***"
        return success_response({"token": masked, "ok": True}, "Token 获取成功")
    except Exception as e:
        return error_response(f"Token 获取失败: {str(e)}")


@wecom_bp.route("/approval-records", methods=["GET"])
@login_required
@admin_required
def approval_records():
    """分页查询审批记录（管理端）"""
    from ..models.approval_record import ApprovalRecord
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    status = request.args.get("status", "")
    query = ApprovalRecord.query.order_by(ApprovalRecord.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [r.to_dict() for r in pagination.items]
    return success_response(data=paginated_response(
        items=items, total=pagination.total, page=page, page_size=page_size,
    ))


@wecom_bp.route("/schedule-records", methods=["GET"])
@login_required
@admin_required
def schedule_records():
    """分页查询日程记录（管理端）"""
    from ..models.schedule_record import ScheduleRecord
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    status = request.args.get("status", "")
    query = ScheduleRecord.query.order_by(ScheduleRecord.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [r.to_dict() for r in pagination.items]
    return success_response(data=paginated_response(
        items=items, total=pagination.total, page=page, page_size=page_size,
    ))


@wecom_bp.route("/approval-records/<int:record_id>/status", methods=["PUT"])
@login_required
@admin_required
def update_approval_status(record_id):
    """更新审批记录状态（管理端手动通过/驳回）"""
    from ..models.approval_record import ApprovalRecord
    from ..extensions import db
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "")
    if new_status not in ("approved", "rejected", "cancelled"):
        return error_response("无效的状态值", 400)
    record = ApprovalRecord.query.get(record_id)
    if not record:
        return error_response("记录不存在", 404)
    record.status = new_status
    db.session.commit()
    return success_response(record.to_dict(), "状态更新成功")


@wecom_bp.route("/approval-submit", methods=["POST"])
@login_required
@admin_required
def admin_submit_approval():
    """管理员代提交审批申请"""
    from ..services.approval_service import approval_service
    from ..models.approval_record import ApprovalRecord
    from ..extensions import db
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "")
    template_name = data.get("template_name", "请假")
    fields = data.get("fields", {})
    if not user_id:
        return error_response("缺少申请人 user_id", 400)
    if not fields:
        return error_response("缺少审批字段", 400)
    resp = approval_service.submit(user_id, template_name, fields)
    if resp.get("errcode", -1) != 0:
        return error_response(f"提交失败: {resp.get('errmsg', '未知错误')}", 500)
    sp_no = resp.get("sp_no", "")
    record = ApprovalRecord(
        user_id=user_id,
        sp_no=sp_no,
        template_name=template_name,
        status="pending",
        fields_json=fields,
    )
    db.session.add(record)
    db.session.commit()
    return success_response(record.to_dict(), "审批提交成功")


@wecom_bp.route("/customer-records", methods=["GET"])
@login_required
@admin_required
def customer_records():
    """分页查询客户运营记录（管理端）"""
    from ..models.customer_record import CustomerRecord
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    action_type = request.args.get("action_type", "")
    query = CustomerRecord.query.order_by(CustomerRecord.created_at.desc())
    if action_type:
        query = query.filter_by(action_type=action_type)
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [r.to_dict() for r in pagination.items]
    return success_response(data=paginated_response(
        items=items, total=pagination.total, page=page, page_size=page_size,
    ))


def _extract_echostr():
    """从原始查询字符串中提取 echostr，仅做百分号解码（不转换 + → 空格）。
    Flask 的 request.args 会把 + 解码为空格，导致 base64 中的 + 签名校验失败。
    """
    from urllib.parse import unquote
    qs = request.query_string.decode("utf-8", errors="replace") if request.query_string else ""
    for param in qs.split("&"):
        if param.startswith("echostr="):
            raw = param[len("echostr="):]
            return unquote(raw)
    return request.args.get("echostr", "")


def _dump_callback_request(method, echostr, msg_signature, timestamp, nonce, token):
    """调试用：将回调请求参数写入文件"""
    import os, json, hashlib
    from datetime import datetime as dt
    dump_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "callback_dump.json")
    try:
        expected_sig = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode()).hexdigest()
        data = {
            "method": method,
            "time": str(dt.now()),
            "echostr": echostr,
            "echostr_len": len(echostr),
            "msg_signature": msg_signature,
            "timestamp": timestamp,
            "nonce": nonce,
            "computed_signature": expected_sig,
            "signature_match": msg_signature == expected_sig,
            "token_len": len(token),
            "raw_qs": request.query_string.decode("utf-8", errors="replace") if request.query_string else "",
            "remote_addr": request.remote_addr or "",
            "user_agent": request.headers.get("User-Agent", "")[:200],
        }
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _dump_all_requests():
    """调试：记录每一次回调请求的完整信息"""
    import os, json
    from datetime import datetime as dt
    dump_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "callback_dump.json")
    try:
        existing = []
        if os.path.exists(dump_path):
            try:
                with open(dump_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    existing = content if isinstance(content, list) else [content]
            except Exception:
                existing = []
        entry = {
            "time": str(dt.now()),
            "method": request.method,
            "remote_addr": request.remote_addr or "",
            "user_agent": request.headers.get("User-Agent", "")[:300],
            "raw_qs": request.query_string.decode("utf-8", errors="replace") if request.query_string else "",
            "body": request.data.decode("utf-8", errors="replace")[:500] if request.data else "",
            "args": dict(request.args),
        }
        existing.append(entry)
        if len(existing) > 20:
            existing = existing[-20:]
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@wecom_bp.route("/callback", methods=["GET", "POST"])
def callback():
    """
    企微回调统一入口
    GET: URL验证 — 回传 echostr 明文
    POST: 事件推送 — 验签→解密→解析→去重→异步分发
    """
    # 调试：记录每一次回调请求（GET 和 POST 都记录）
    _dump_all_requests()

    token = current_app.config["WECOM_TOKEN"]
    encoding_aes_key = current_app.config["WECOM_ENCODING_AES_KEY"]
    corp_id = current_app.config["WECOM_CORP_ID"]

    msg_signature = request.args.get("msg_signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    # ==================== GET：URL 验证 ====================
    if request.method == "GET":
        echostr = _extract_echostr()
        if verify_signature(token, timestamp, nonce, echostr, msg_signature):
            _, plain = decrypt_message(encoding_aes_key, echostr)
            current_app.logger.info(f"[企微回调] URL验证成功")
            return plain
        import hashlib
        expected = hashlib.sha1("".join(sorted([token, timestamp, nonce, echostr])).encode()).hexdigest()
        current_app.logger.error(
            f"[企微回调] URL验证签名失败 | "
            f"received={msg_signature} | computed={expected}"
        )
        return "signature verify failed", 403

    # ==================== POST：事件推送 ====================
    # 1. 读取加密的 XML 体
    raw_xml = request.data.decode("utf-8")
    try:
        root = ET.fromstring(raw_xml)
        encrypted_msg = root.findtext("Encrypt", "")
    except ET.ParseError:
        current_app.logger.error("[企微回调] XML解析失败")
        return "xml parse error", 400

    # 2. 验签
    if not verify_message_signature(token, timestamp, nonce, encrypted_msg, msg_signature):
        current_app.logger.error("[企微回调] 消息签名验证失败")
        return "signature verify failed", 403

    # 3. 解密
    err, decrypted_xml = decrypt_message(encoding_aes_key, encrypted_msg)
    if err != 0:
        current_app.logger.error(f"[企微回调] 解密失败: {decrypted_xml}")
        return "decrypt failed", 400

    # 4. 解析事件 XML
    try:
        event_root = ET.fromstring(decrypted_xml)
    except ET.ParseError:
        current_app.logger.error("[企微回调] 事件XML解析失败")
        return "xml parse error", 400

    # 提取关键字段
    msg_id = event_root.findtext("MsgId", "")
    event_type = event_root.findtext("Event", "")
    create_time = event_root.findtext("CreateTime", "")
    event_key = event_root.findtext("EventKey", "")

    # 5. 幂等去重（MsgId + Event + CreateTime）
    dedup_key = f"wecom:dedup:{msg_id}:{event_type}:{create_time}:{event_key}"
    if _redis_ok():
        if redis_client.exists(dedup_key):
            current_app.logger.info(f"[企微回调] 重复事件已忽略: {dedup_key}")
            return "success"
        redis_client.setex(dedup_key, 86400, "1")  # 24h TTL

    # 6. 提取事件数据
    parsed_data = {
        "msg_id": msg_id,
        "event_type": event_type,
        "create_time": create_time,
        "event_key": event_key,
        "from_user": event_root.findtext("FromUserName", ""),
        "raw_xml": decrypted_xml,
    }
    # 解析子节点（不同事件类型有不同的子节点）
    for child in event_root:
        if child.tag not in ("ToUserName", "FromUserName", "CreateTime", "Event", "MsgId", "AgentID", "EventKey"):
            parsed_data[child.tag.lower()] = child.text

    # 7. 异步分发处理（不阻塞 5 秒响应时限）
    import sys
    sys.stderr.write(f"[DEBUG] POST dispatch: event_type={event_type} msgtype={parsed_data.get('msgtype','')} from={parsed_data.get('from_user','')}\n")
    sys.stderr.flush()
    app = current_app._get_current_object()
    _executor.submit(_dispatch_event, app, event_type, parsed_data)

    # 8. 立即返回 200（企微要求 5 秒内响应）
    return "success"


def _dispatch_event(app, event_type, parsed_data):
    """异步事件分发（在 executor 中执行）"""
    import os, json, traceback
    from datetime import datetime as dt
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "dispatch_log.json")
    with app.app_context():
        try:
            result = event_service.route_event(event_type, parsed_data)
            entry = {"time": str(dt.now()), "event_type": event_type, "result": str(result), "status": "ok"}
        except Exception as e:
            entry = {"time": str(dt.now()), "event_type": event_type, "error": str(e), "traceback": traceback.format_exc(), "status": "error"}
            current_app.logger.error(f"[企微回调] 事件处理异常: {e}", exc_info=True)
    try:
        existing = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = [existing]
        existing.append(entry)
        if len(existing) > 50:
            existing = existing[-50:]
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
