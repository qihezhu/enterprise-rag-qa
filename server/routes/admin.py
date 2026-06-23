"""
管理员后台路由模块
提供数据统计仪表盘、用户管理、系统日志查询等管理功能
所有接口均需要管理员权限
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, g, current_app
from sqlalchemy import func, text
from ..extensions import db
from ..models.user import User
from ..models.document import Document
from ..models.conversation import Conversation
from ..models.system_log import SystemLog
from ..middleware.auth_middleware import login_required, admin_required
from ..utils.helpers import success_response, error_response, paginated_response

# 创建管理员蓝图，URL前缀 /api/admin
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/statistics", methods=["GET"])
@login_required
@admin_required
def get_statistics():
    """
    管理员仪表盘统计数据接口
    返回：用户总数、文档总数、分块总数、今日/累计问答数、
          近7天提问趋势、文档类型分布、最近活动动态
    """
    # ==================== 基础统计数据 ====================
    user_count = User.query.filter(User.status == 1).count()
    document_count = Document.query.filter(Document.status == 1).count()

    # 所有文档的总分块数
    total_chunks = db.session.query(func.sum(Document.chunk_count))\
        .filter(Document.status == 1).scalar() or 0

    # 今日问答数量
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    qa_count_today = Conversation.query.filter(
        Conversation.created_at >= today_start
    ).count()

    # 累计问答总数
    qa_count_total = Conversation.query.count()

    # ==================== 近7天提问趋势 ====================
    daily_qa_trend = []
    for i in range(6, -1, -1):
        day_start = (datetime.now() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Conversation.query.filter(
            Conversation.created_at >= day_start,
            Conversation.created_at < day_end,
        ).count()
        daily_qa_trend.append({
            "date": day_start.strftime("%m-%d"),
            "count": count,
        })

    # ==================== 文档类型分布 ====================
    doc_type_query = db.session.query(
        Document.file_type, func.count(Document.id)
    ).filter(
        Document.status == 1,
        Document.file_type.isnot(None),
    ).group_by(Document.file_type).all()

    doc_type_distribution = [
        {"type": file_type or "未知", "count": cnt}
        for file_type, cnt in doc_type_query
    ]

    # ==================== 最近活动动态（最新10条日志） ====================
    recent_logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(10).all()
    recent_activities = [
        {
            "user": log.user.username if log.user else "匿名",
            "action": log.action,
            "detail": log.description or "",
            "time": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        }
        for log in recent_logs
    ]

    return success_response(data={
        "user_count": user_count,
        "document_count": document_count,
        "total_chunks": total_chunks,
        "qa_count_today": qa_count_today,
        "qa_count_total": qa_count_total,
        "daily_qa_trend": daily_qa_trend,
        "doc_type_distribution": doc_type_distribution,
        "recent_activities": recent_activities,
    })


# ==================== 用户管理 ====================

@admin_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    """
    用户列表接口（管理员视角）
    查询参数：page(页码), page_size(每页条数), keyword(搜索关键词)
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 10, type=int)
    keyword = request.args.get("keyword", "").strip()

    query = User.query
    if keyword:
        query = query.filter(
            db.or_(
                User.username.contains(keyword),
                User.email.contains(keyword),
            )
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    items = [user.to_dict() for user in pagination.items]

    return success_response(data=paginated_response(
        items=items,
        total=pagination.total,
        page=page,
        page_size=page_size,
    ))


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
@admin_required
def update_user(user_id):
    """
    管理员修改用户信息（状态、角色）
    请求体：{"status": 1, "role": "admin"}  两个字段均为可选
    注意：不能修改自己的角色
    """
    user = User.query.get(user_id)
    if user is None:
        return error_response("用户不存在", 404)

    data = request.get_json()
    if not data:
        return error_response("请提供要修改的信息", 400)

    # 修改状态（启用/禁用）
    if "status" in data:
        if data["status"] not in [0, 1]:
            return error_response("状态值无效", 400)
        user.status = data["status"]

    # 修改角色
    if "role" in data:
        if data["role"] not in ["admin", "user"]:
            return error_response("角色值无效", 400)
        if user.id == g.current_user.id:
            return error_response("不能修改自己的角色", 400)
        user.role = data["role"]

    user.updated_at = datetime.now()
    db.session.commit()

    # 记录日志
    log = SystemLog(
        user_id=g.current_user.id,
        action="USER_UPDATE",
        description=f"管理员修改用户 {user.username} 的信息",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(data=user.to_dict(), message="用户信息更新成功")


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    """
    管理员删除用户
    注意：不能删除自己，不能删除其他管理员
    """
    user = User.query.get(user_id)
    if user is None:
        return error_response("用户不存在", 404)

    if user.id == g.current_user.id:
        return error_response("不能删除自己", 400)

    if user.is_admin():
        return error_response("不能删除其他管理员账号", 400)

    username = user.username
    db.session.delete(user)

    log = SystemLog(
        user_id=g.current_user.id,
        action="USER_DELETE",
        description=f"管理员删除用户: {username}",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(message=f"用户 {username} 已删除")


# ==================== 系统日志 ====================

@admin_bp.route("/logs", methods=["GET"])
@login_required
@admin_required
def list_logs():
    """
    系统日志列表接口（分页 + 操作类型筛选）
    查询参数：page(页码), page_size(每页条数), action(操作类型筛选)
    """
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    action = request.args.get("action", "").strip()

    query = SystemLog.query
    if action:
        query = query.filter(SystemLog.action == action)

    pagination = query.order_by(SystemLog.created_at.desc()).paginate(
        page=page, per_page=page_size, error_out=False
    )

    items = [log.to_dict() for log in pagination.items]

    return success_response(data=paginated_response(
        items=items,
        total=pagination.total,
        page=page,
        page_size=page_size,
    ))


@admin_bp.route("/metrics", methods=["GET"])
@login_required
@admin_required
def get_metrics():
    """获取 Agent Tool 调用指标"""
    from ..monitoring.metrics import get_metrics
    return success_response(data=get_metrics())
