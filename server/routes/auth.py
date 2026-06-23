"""
认证路由模块
处理用户登录、注册、获取当前用户信息等请求
"""
from flask import Blueprint, request, g
from ..extensions import db
from ..models.user import User
from ..models.system_log import SystemLog
from ..middleware.auth_middleware import generate_token, login_required
from ..utils.helpers import success_response, error_response

# 创建认证蓝图，URL前缀 /api/auth
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录接口
    请求体：{"username": "xxx", "password": "xxx", "role": "admin"}   role为必填：admin或user
    管理员账号只能登录管理员后台，普通用户只能登录用户端
    成功返回：{code: 200, data: {token, user}}
    """
    data = request.get_json()
    if not data:
        return error_response("请提供登录信息", 400)

    username = data.get("username", "").strip()
    password = data.get("password", "")
    login_role = data.get("role", "").strip()  # 前端传入的登录端：admin 或 user

    if not username or not password:
        return error_response("用户名和密码不能为空", 400)

    if login_role not in ("admin", "user"):
        return error_response("请选择正确的登录端", 400)

    # 查询用户
    user = User.query.filter_by(username=username).first()
    if user is None:
        return error_response("用户名或密码错误", 401)

    # 验证密码（MD5加密后比对）
    if not user.check_password(password):
        return error_response("用户名或密码错误", 401)

    # 检查账号状态
    if not user.is_active():
        return error_response("账号已被禁用，请联系管理员", 403)

    # 角色校验：管理员的账号只能登录管理员端，普通用户只能登录用户端
    if user.role != login_role:
        if login_role == "admin":
            return error_response("该账号不是管理员，无法登录管理员后台", 403)
        else:
            return error_response("该账号是管理员，请使用管理员登录入口", 403)

    # 生成JWT Token
    token = generate_token(user)

    # 记录登录日志
    log = SystemLog(
        user_id=user.id,
        action="LOGIN",
        description=f"用户 {user.username} 登录系统（{'管理员端' if login_role == 'admin' else '用户端'}）",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(
        data={
            "token": token,
            "user": user.to_dict(),
        },
        message="登录成功",
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    用户注册接口（注册后默认为普通用户角色）
    请求体：{"username": "xxx", "password": "xxx", "email": "xxx@xx.com"}
    成功返回：{code: 201, data: {id, username}}
    """
    data = request.get_json()
    if not data:
        return error_response("请提供注册信息", 400)

    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip()

    if not username or not password:
        return error_response("用户名和密码不能为空", 400)

    if len(username) < 2 or len(username) > 50:
        return error_response("用户名长度须在2-50个字符之间", 400)

    if len(password) < 6:
        return error_response("密码长度不能少于6位", 400)

    # 检查用户名是否已存在
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return error_response("用户名已存在", 409)

    # 创建用户，密码MD5加密
    new_user = User(
        username=username,
        password=User.hash_password(password),
        role="user",
        email=email if email else None,
    )
    db.session.add(new_user)

    # 记录注册日志
    log = SystemLog(
        user_id=None,  # 注册时还没有用户ID
        action="USER_REGISTER",
        description=f"新用户 {username} 注册",
        ip_address=request.remote_addr,
    )
    db.session.add(log)
    db.session.commit()

    return success_response(
        data=new_user.to_dict(),
        message="注册成功",
        code=201,
    )


@auth_bp.route("/userinfo", methods=["GET"])
@login_required
def get_userinfo():
    """
    获取当前登录用户信息
    需要在请求头中携带 Authorization: Bearer <token>
    返回：当前登录用户的详细信息
    """
    return success_response(data=g.current_user.to_dict())
