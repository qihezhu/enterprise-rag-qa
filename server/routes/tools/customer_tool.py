"""
客户运营 Tool 端点（千问Agent平台调用）
打标签、创建群发任务、查跟进记录
"""
from flask import request, current_app
from ...services.customer_service import customer_service
from ...models.customer_record import CustomerRecord
from ...middleware.auth_middleware import require_tool_api_key
from ...utils.helpers import success_response, error_response, clean_tool_inputs
from ...extensions import db

from .approval_tool import tool_bp, _resolve_user_id


@tool_bp.route("/customer/search", methods=["POST"])
@require_tool_api_key
def search_customer():
    """
    按姓名搜索外部联系人
    输入: {"name": "文玺", "user_id": "XuQi"}
    输出: {"results": [{"external_userid": "wmxxxxx", "name": "文玺", ...}]}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    name = data.get("name", "") or data.get("query", "")
    user_id = data.get("user_id", "") or data.get("name_param", "")

    if not name:
        return error_response("缺少 name 参数", 400)

    # 解析中文名为 userid；空时回退到默认用户
    resolved = _resolve_user_id(user_id) if user_id else ""
    if resolved:
        user_id = resolved
    if not user_id:
        user_id = "XuQi"

    results = customer_service.search_external_contact(user_id, name)
    return success_response({"results": results, "total": len(results)}, "查询完成")


@tool_bp.route("/customer/tag", methods=["POST"])
@require_tool_api_key
def mark_tag():
    """
    为客户打标签
    输入: {"user_id": "zhangsan", "external_userid": "wmxxxxx", "tag_names": ["VIP客户", "重点跟进"]}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    user_id = data.get("user_id", "")
    external_userid = data.get("external_userid", "")
    tag_names = data.get("tag_names", [])

    if not user_id or not external_userid:
        return error_response(f"缺少必填参数 [raw data: {data}]", 400)
    if not tag_names:
        return error_response("缺少 tag_names 参数", 400)

    # 解析中文名为 userid；空时回退到默认用户
    resolved = _resolve_user_id(user_id) if user_id else ""
    if resolved:
        user_id = resolved
    if not user_id:
        user_id = "XuQi"

    resp = customer_service.mark_tag(user_id, external_userid, tag_names)

    # 记录操作
    record = CustomerRecord(
        user_id=user_id,
        external_userid=external_userid,
        action_type="tag",
        detail_json={"tag_names": tag_names},
        api_result=resp,
    )
    db.session.add(record)
    db.session.commit()

    if resp.get("errcode", -1) != 0:
        return error_response(resp.get("errmsg", "打标签失败"), 500)
    return success_response({"tags_applied": tag_names, "record_id": record.id}, "标签已添加")


@tool_bp.route("/customer/broadcast", methods=["POST"])
@require_tool_api_key
def create_broadcast():
    """
    创建群发任务
    输入: {"user_id": "zhangsan", "external_userid": "wmxxxxx", "text": "您好，关于..."}
    本地计数拦截，防止超过每人每天1条限制
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    user_id = data.get("user_id", "")
    external_userid = data.get("external_userid", "")
    text = data.get("text", "")

    if not user_id or not external_userid or not text:
        return error_response("缺少必填参数", 400)

    resp = customer_service.create_broadcast(user_id, external_userid, text)

    # 记录操作
    record = CustomerRecord(
        user_id=user_id,
        external_userid=external_userid,
        action_type="broadcast",
        detail_json={"text": text},
        api_result=resp,
    )
    db.session.add(record)
    db.session.commit()

    if resp.get("errcode", -1) != 0:
        return error_response(resp.get("errmsg", "群发失败"), 500)
    return success_response({"msg_id": resp.get("msgid", ""), "record_id": record.id}, "群发已创建")


@tool_bp.route("/customer/check-follow", methods=["POST"])
@require_tool_api_key
def check_follow():
    """
    查询客户跟进信息
    输入: {"external_userid": "wmxxxxx"}
    输出: {name, tags, follow_users, last_contact}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    external_userid = data.get("external_userid", "")

    if not external_userid:
        return error_response("缺少 external_userid 参数", 400)

    result = customer_service.get_follow_up(external_userid)
    if "errcode" in result:
        return error_response(result.get("errmsg", "查询失败"), 500)
    return success_response(result, "查询完成")
