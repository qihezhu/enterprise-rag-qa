"""
联系人 Tool 端点（千问Agent平台调用）
提供成员搜索、部门查询、汇报链查询
"""
from flask import Blueprint, request
from ...services.contact_service import contact_service
from ...middleware.auth_middleware import require_tool_api_key
from ...utils.helpers import success_response, error_response, clean_tool_inputs

# 注册到已有的 tool_bp
from .approval_tool import tool_bp


@tool_bp.route("/contact/search", methods=["POST"])
@require_tool_api_key
def search_user():
    """
    搜索成员（姓名/手机号）
    输入: {"query": "张三 或 13812345678"}
    输出: {"results": [{userid, name, department, position, mobile, email}], "total": N}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    query = data.get("query", "")
    if not query:
        return error_response("缺少 query 参数", 400)
    result = contact_service.search_user(query)
    return success_response(result, "搜索完成")


@tool_bp.route("/contact/department", methods=["POST"])
@require_tool_api_key
def get_department():
    """
    获取部门成员
    输入: {"dept_id": 1, "recursive": true}
    输出: {"dept_id": 1, "members": [...], "total": N}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    dept_id = data.get("dept_id", 1)
    recursive = data.get("recursive", True)
    result = contact_service.get_department_members(dept_id, recursive)
    return success_response(result, "查询完成")


@tool_bp.route("/contact/report-chain", methods=["POST"])
@require_tool_api_key
def get_report_chain():
    """
    获取汇报链（支持 userid 或姓名）
    输入: {"user_id": "zhangsan"} 或 {"name": "张三"}
    输出: {"user_id": "zhangsan", "chain": [{name, position, department}]}
    """
    data = clean_tool_inputs(request.get_json(silent=True) or {})
    user_id = data.get("user_id", "")
    name = data.get("name", "")
    if not user_id and not name:
        return error_response("缺少 user_id 或 name 参数", 400)
    # 如果传入姓名，先搜索找到 userid
    if not user_id and name:
        search_result = contact_service.search_user(name)
        users = search_result.get("results", [])
        if users:
            user_id = users[0]["userid"]
        else:
            return error_response(f"未找到成员: {name}", 404)
    result = contact_service.get_report_chain(user_id)
    return success_response(result, "查询完成")
