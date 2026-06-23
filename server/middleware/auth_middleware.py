"""
认证中间件模块
提供JWT Token生成、解析以及登录/管理员权限验证装饰器
"""
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app
from ..models.user import User
from ..utils.helpers import error_response


def generate_token(user):
    """
    为用户生成JWT访问令牌
    参数：
        user: User模型对象
    返回：
        JWT token字符串
    """
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=current_app.config.get("JWT_EXPIRATION_HOURS", 24)),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    return token


def decode_token(token):
    """
    解析JWT令牌
    参数：
        token: JWT token字符串
    返回：
        解析成功返回payload字典，失败返回None
    """
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token已过期
    except jwt.InvalidTokenError:
        return None  # Token无效


def login_required(func):
    """
    登录验证装饰器
    验证请求头中的Authorization Bearer Token，将当前用户注入g.current_user
    使用方法：在路由函数上添加 @login_required
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 从请求头中获取token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return error_response("请先登录", 401)

        token = auth_header.split("Bearer ")[1].strip()
        if not token:
            return error_response("请先登录", 401)

        # 解析token
        payload = decode_token(token)
        if payload is None:
            return error_response("登录已过期，请重新登录", 401)

        # 查询用户
        user = User.query.get(payload.get("user_id"))
        if user is None:
            return error_response("用户不存在", 401)

        if not user.is_active():
            return error_response("账号已被禁用，请联系管理员", 403)

        # 将当前用户注入flask.g
        g.current_user = user
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    """
    管理员权限验证装饰器（需配合 @login_required 使用）
    验证当前登录用户是否为管理员角色
    使用方法：在路由函数上添加 @login_required 后再添加 @admin_required
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not g.current_user.is_admin():
            return error_response("无权限，仅管理员可操作", 403)
        return func(*args, **kwargs)

    return wrapper


def require_tool_api_key(func):
    """
    Tool API Key 验证装饰器
    支持三种认证方式（按优先级）：
    1. X-Tool-API-Key 请求头
    2. Authorization: Bearer <token>
    3. X-Nexus-Token 请求头（百炼平台默认发送）
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.headers.get("X-Tool-API-Key", "")
        if not api_key:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                api_key = auth[7:]
        if not api_key:
            api_key = request.headers.get("X-Nexus-Token", "")
        expected = current_app.config.get("QWEN_TOOL_API_KEY", "")
        if not expected:
            return error_response("服务未配置 Tool API Key", 500)
        if api_key != expected:
            return error_response("Unauthorized", 401)
        return func(*args, **kwargs)

    return wrapper
