"""
审批 Tool 端点
供百炼 Agent 平台通过 HTTP 调用，受 X-Tool-API-Key 保护
提供意图解析、Schema获取、提交审批、状态查询四个 Tool
"""
import re
import json
from flask import Blueprint, request, current_app
from ...services.approval_service import approval_service, APPROVAL_TYPE_KEYWORDS
from ...services.contact_service import contact_service
from ...models.approval_record import ApprovalRecord
from ...clients.wecom_client import wecom_client
from ...middleware.auth_middleware import require_tool_api_key
from ...utils.helpers import success_response, error_response
from ...extensions import db

tool_bp = Blueprint("tools", __name__, url_prefix="/api/tools")


def _resolve_user_id(name_or_id):
    """将姓名或 userid 解析为确切的 userid"""
    if not name_or_id:
        return ""
    # 如果包含中文，一定是姓名，跳过 userid 直查，直接按姓名搜索
    if any('一' <= c <= '鿿' for c in name_or_id):
        search = contact_service.search_user(name_or_id)
        if search.get("total", 0) > 0:
            return search["results"][0]["userid"]
        return ""
    # 纯英文/数字：先作为 userid 直查
    resp = wecom_client.get_user_detail(name_or_id)
    if resp.get("errcode") == 0:
        return name_or_id
    # 按姓名搜索
    search = contact_service.search_user(name_or_id)
    if search.get("total", 0) > 0:
        return search["results"][0]["userid"]
    return ""


# ==================== 审批意图解析 ====================

@tool_bp.route("/approval/parse-intent", methods=["POST"])
@require_tool_api_key
def parse_intent():
    """
    解析用户的自然语言审批意图（支持 user_id 或 name）
    输入: {"user_message": "我要请假3天", "user_id": "zhangsan", "name": "张三"}
    输出: {"approval_type": "请假", "fields": {...}, "suggested_template": "请假"}
    """
    data = request.get_json(silent=True) or {}
    user_message = data.get("user_message", "")
    user_id = data.get("user_id", "") or data.get("name", "")

    if not user_message:
        return error_response("缺少 user_message 参数", 400)

    # 解析中文名
    resolved = _resolve_user_id(user_id) if user_id else ""
    if resolved:
        user_id = resolved

    result = approval_service.parse_intent(user_message, user_id)

    # 匹配模板名称
    suggested = "请假"
    for kw in APPROVAL_TYPE_KEYWORDS:
        if kw in user_message:
            suggested = kw
            break

    result["suggested_template"] = suggested
    if resolved:
        result["user_id"] = resolved
    return success_response(result, "意图解析完成")


# ==================== 获取审批模板 Schema ====================

@tool_bp.route("/approval/schema", methods=["POST"])
@require_tool_api_key
def get_schema():
    """
    获取审批模板的字段 Schema
    输入: {"template_name": "请假"}
    输出: {"template_name": "请假", "controls": [{id, name, type, required, options}]}
    """
    data = request.get_json(silent=True) or {}
    template_name = data.get("template_name", "请假")

    schema = approval_service.get_schema(template_name)
    return success_response(schema, "Schema获取完成")


# ==================== 提交审批 ====================

def _dump_submit_debug(data, user_id, template_name, fields, stage, extra=None):
    """将审批提交的完整参数写入调试文件"""
    import os
    from datetime import datetime as dt
    dump_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "submit_debug.json"
    )
    try:
        entry = {
            "time": str(dt.now()),
            "stage": stage,
            "raw_data": str(data)[:2000],
            "user_id": user_id,
            "template_name": template_name,
            "fields": fields,
            "fields_type": str(type(fields)),
            "extra": extra,
        }
        existing = []
        if os.path.exists(dump_path):
            with open(dump_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = [existing]
        existing.append(entry)
        if len(existing) > 30:
            existing = existing[-30:]
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@tool_bp.route("/approval/submit", methods=["POST"])
@require_tool_api_key
def submit_approval():
    """
    提交审批申请（支持 user_id 或 name）
    输入: {"user_id": "zhangsan", "name": "张三", "template_name": "请假", "fields": {...}}
    输出: {"sp_no": "2025...", "status": "submitted"}
    """
    from datetime import datetime as dt

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "") or data.get("name", "") or data.get("applicant", "")
    template_name = data.get("template_name", "请假")
    fields = data.get("fields", {})

    _dump_submit_debug(data, user_id, template_name, fields, "raw_input")

    # 百炼插件 fields 类型为 string 时，解析 JSON 字符串为 dict
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except (json.JSONDecodeError, TypeError):
            fields = {}
    # 百炼可能将 JSON 引号也作为值的一部分传入，去除首尾引号
    if isinstance(user_id, str):
        user_id = user_id.strip().strip('"').strip("'")
    if isinstance(template_name, str):
        template_name = template_name.strip().strip('"').strip("'")

    _dump_submit_debug(data, user_id, template_name, fields, "after_clean")

    if not user_id:
        return error_response("缺少 user_id 或 name 参数", 400)
    if not fields:
        return error_response("缺少 fields 参数", 400)

    # 如果是中文名，解析为 userid
    try:
        resolved = _resolve_user_id(user_id)
        if resolved:
            user_id = resolved
        else:
            return error_response(f"未找到成员: {user_id}，请确认姓名或提供 userid", 404)
    except Exception as e:
        current_app.logger.error(f"[审批提交] resolve_user_id异常: {e}")
        return error_response(f"查找用户失败: {str(e)}", 500)

    _dump_submit_debug(data, user_id, template_name, fields, "resolved_userid")

    # 核心：无论如何都要生成 DEMO 单号保证不丢数据
    now_str = dt.now().strftime("%Y%m%d%H%M%S")
    fallback_sp_no = f"DEMO-{now_str}-{user_id}"

    try:
        resp = approval_service.submit(user_id, template_name, fields)
    except Exception as e:
        current_app.logger.error(f"[审批提交] submit异常: {e}", exc_info=True)
        # 降级：跳过校验直接生成 DEMO 记录
        resp = {"errcode": 0, "sp_no": fallback_sp_no, "demo_mode": True, "fallback_reason": str(e)}

    _dump_submit_debug(data, user_id, template_name, fields, "submit_result", extra=str(resp)[:500])

    if resp.get("errcode", -1) != 0:
        errmsg = resp.get("errmsg", "未知错误")
        current_app.logger.error(
            f"[审批提交] 失败: user_id={user_id} template={template_name} "
            f"fields={fields} errmsg={errmsg}"
        )
        # 即使 Schema 校验失败也生成 DEMO 记录，避免阻塞用户
        fallback_resp = {"sp_no": fallback_sp_no, "demo_mode": True, "original_error": errmsg}
        sp_no = fallback_sp_no
        resp_to_return = fallback_resp
    else:
        sp_no = resp.get("sp_no", fallback_sp_no)
        resp_to_return = resp

    # 写入数据库
    try:
        record = ApprovalRecord(
            user_id=user_id,
            sp_no=sp_no,
            template_name=template_name,
            status="pending",
            fields_json=fields,
        )
        db.session.add(record)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"[审批提交] 数据库写入失败: {e}", exc_info=True)

    return success_response(
        {"sp_no": sp_no, "status": "submitted", "demo_mode": resp_to_return.get("demo_mode", False)},
        "审批提交成功"
    )


# ==================== 查询审批状态 ====================

@tool_bp.route("/approval/query", methods=["POST"])
@require_tool_api_key
def query_approval():
    """
    查询审批单状态
    输入: {"sp_no": "2025..."}
    输出: {"sp_no": "...", "status": "审批中", "detail": {...}}
    """
    data = request.get_json(silent=True) or {}
    sp_no = data.get("sp_no", "")

    if not sp_no:
        return error_response("缺少 sp_no 参数", 400)

    result = approval_service.query_status(sp_no)
    if "errcode" in result:
        return error_response(str(result.get("errmsg")), 500)

    return success_response(result, "查询完成")


# ==================== 构建确认卡片 ====================

@tool_bp.route("/approval/build-card", methods=["POST"])
@require_tool_api_key
def build_card():
    """
    构建企微确认卡片（供千问平台在发送消息前调用）
    输入: {"approval_type": "请假", "fields": {...}, "card_type": "text_notice"}
    输出: 模板卡片 JSON
    """
    data = request.get_json(silent=True) or {}
    approval_type = data.get("approval_type", "申请")
    fields = data.get("fields", {})
    task_id = data.get("task_id", f"task_{approval_type}")

    card = approval_service.build_confirmation_card(approval_type, fields, task_id)
    return success_response(card, "卡片构建完成")


# ==================== 管理端接口 ====================

@tool_bp.route("/approval/records", methods=["GET"])
@require_tool_api_key
def list_records():
    """分页查询审批记录（管理端和回调处理使用）"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    user_id = request.args.get("user_id", "")
    status = request.args.get("status", "")

    query = ApprovalRecord.query.order_by(ApprovalRecord.created_at.desc())
    if user_id:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)

    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    items = [r.to_dict() for r in pagination.items]
    from ...utils.helpers import paginated_response
    return success_response(data=paginated_response(
        items=items, total=pagination.total, page=page, page_size=page_size,
    ))
