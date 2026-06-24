"""
API 单元测试（pytest 风格，CI 中可运行）
使用 conftest.py 的 client fixture，无需启动真实服务
覆盖：认证、权限、Tool API Key、文档管理、管理员接口
"""
import json
import hashlib
import pytest
from server.models.user import User
from server.extensions import db


# ==================== 辅助函数 ====================

def post_json(client, path, body=None, headers=None):
    """发送 POST JSON 请求，返回 response 对象"""
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return client.post(path, data=json.dumps(body) if body else None, headers=h)


def get_json(client, path, headers=None):
    """发送 GET 请求，返回 response 对象"""
    return client.get(path, headers=headers or {})


def auth_header(token):
    """构造 Bearer Token 请求头"""
    return {"Authorization": f"Bearer {token}"}


def login(client, username, password, role):
    """登录并返回 token"""
    r = post_json(client, "/api/auth/login",
                  {"username": username, "password": password, "role": role})
    data = r.get_json()
    return data.get("data", {}).get("token", "") if r.status_code == 200 else ""


# ==================== 测试数据 fixture ====================

@pytest.fixture
def seed_users(app):
    """插入测试用户（admin + 普通用户）"""
    with app.app_context():
        pwd = hashlib.md5("123456".encode("utf-8")).hexdigest()
        admin = User(username="admin", password=pwd, role="admin",
                     email="admin@test.com", phone="13800000001", status=1)
        user = User(username="lisi", password=pwd, role="user",
                    email="lisi@test.com", phone="13800000003", status=1)
        db.session.add_all([admin, user])
        db.session.commit()
        return {"admin_id": admin.id, "user_id": user.id}


# ============================================================
# 一、用户认证与权限
# ============================================================

class TestAuth:
    """认证模块测试"""

    def test_admin_login_success(self, client, seed_users):
        """管理员登录成功"""
        r = post_json(client, "/api/auth/login",
                      {"username": "admin", "password": "123456", "role": "admin"})
        assert r.status_code == 200
        data = r.get_json()
        assert data["code"] == 200
        assert "token" in data["data"]

    def test_user_login_success(self, client, seed_users):
        """普通用户登录成功"""
        r = post_json(client, "/api/auth/login",
                      {"username": "lisi", "password": "123456", "role": "user"})
        assert r.status_code == 200
        assert "token" in r.get_json()["data"]

    def test_wrong_password_rejected(self, client, seed_users):
        """密码错误被拒绝"""
        r = post_json(client, "/api/auth/login",
                      {"username": "admin", "password": "wrong", "role": "admin"})
        assert r.status_code == 401

    def test_role_mismatch_rejected(self, client, seed_users):
        """角色不匹配被拒绝（普通用户登管理端）"""
        r = post_json(client, "/api/auth/login",
                      {"username": "lisi", "password": "123456", "role": "admin"})
        assert r.status_code == 403

    def test_missing_token_rejected(self, client):
        """未携带 Token 访问受保护接口被拒绝"""
        r = get_json(client, "/api/auth/userinfo")
        assert r.status_code == 401

    def test_fake_token_rejected(self, client):
        """伪造 Token 被拒绝"""
        r = get_json(client, "/api/auth/userinfo",
                     headers=auth_header("fake_token_12345"))
        assert r.status_code == 401

    def test_get_userinfo_success(self, client, seed_users):
        """已登录用户获取个人信息"""
        token = login(client, "admin", "123456", "admin")
        r = get_json(client, "/api/auth/userinfo", headers=auth_header(token))
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["username"] == "admin"
        assert data["role"] == "admin"

    def test_register_success(self, client, seed_users):
        """注册新用户成功"""
        r = post_json(client, "/api/auth/register",
                      {"username": "newuser", "password": "123456",
                       "email": "new@test.com"})
        assert r.status_code == 201

    def test_register_duplicate_rejected(self, client, seed_users):
        """重复用户名注册被拒绝"""
        r = post_json(client, "/api/auth/register",
                      {"username": "admin", "password": "123456"})
        assert r.status_code == 409

    def test_register_short_password_rejected(self, client, seed_users):
        """短密码注册被拒绝"""
        r = post_json(client, "/api/auth/register",
                      {"username": "shortpw", "password": "12"})
        assert r.status_code == 400


# ============================================================
# 二、Tool API Key 认证
# ============================================================

class TestToolAuth:
    """Tool 端点 API Key 认证测试"""

    def test_tool_without_apikey_rejected(self, client):
        """无 API Key 访问 Tool 被拒绝"""
        r = post_json(client, "/api/tools/approval/parse-intent",
                      {"user_message": "我要请假3天"})
        assert r.status_code == 401

    def test_tool_with_wrong_apikey_rejected(self, client):
        """错误 API Key 被拒绝"""
        r = post_json(client, "/api/tools/approval/parse-intent",
                      {"user_message": "我要请假3天"},
                      headers={"X-Tool-API-Key": "wrong_key"})
        assert r.status_code == 401

    def test_tool_with_bearer_token_accepted(self, client):
        """Bearer Token 方式认证通过（认证层通过即可，业务错误算 400）"""
        r = post_json(client, "/api/tools/approval/parse-intent",
                      {"user_message": "我要请假3天"},
                      headers={"Authorization": "Bearer test_api_key"})
        assert r.status_code in (200, 400)

    def test_tool_with_nexus_token_accepted(self, client):
        """X-Nexus-Token 方式认证通过（百炼平台默认发送）"""
        r = post_json(client, "/api/tools/approval/parse-intent",
                      {"user_message": "我要请假3天"},
                      headers={"X-Nexus-Token": "test_api_key"})
        assert r.status_code in (200, 400)


# ============================================================
# 三、文档管理
# ============================================================

class TestDocument:
    """文档管理模块测试"""

    def test_get_documents_requires_auth(self, client):
        """未登录访问文档列表被拒绝"""
        r = get_json(client, "/api/documents")
        assert r.status_code == 401

    def test_get_documents_success(self, client, seed_users):
        """登录用户获取文档列表"""
        token = login(client, "lisi", "123456", "user")
        r = get_json(client, "/api/documents", headers=auth_header(token))
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "items" in data
        assert "total" in data

    def test_upload_without_file_rejected(self, client, seed_users):
        """上传文档未提供文件被拒绝"""
        token = login(client, "lisi", "123456", "user")
        r = client.post("/api/documents", headers=auth_header(token))
        assert r.status_code == 400


# ============================================================
# 四、问答历史
# ============================================================

class TestQAHistory:
    """问答历史模块测试"""

    def test_get_history_requires_auth(self, client):
        """未登录访问对话历史被拒绝"""
        r = get_json(client, "/api/qa/history")
        assert r.status_code == 401

    def test_get_history_success(self, client, seed_users):
        """登录用户获取对话历史"""
        token = login(client, "lisi", "123456", "user")
        r = get_json(client, "/api/qa/history", headers=auth_header(token))
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "items" in data

    def test_ask_empty_question_rejected(self, client, seed_users):
        """空问题被拒绝"""
        token = login(client, "lisi", "123456", "user")
        r = post_json(client, "/api/qa/ask",
                      {"question": ""}, headers=auth_header(token))
        assert r.status_code == 400


# ============================================================
# 五、管理员接口
# ============================================================

class TestAdmin:
    """管理员权限测试"""

    def test_admin_statistics_requires_admin(self, client, seed_users):
        """普通用户访问管理端统计被拒绝"""
        token = login(client, "lisi", "123456", "user")
        r = get_json(client, "/api/admin/statistics", headers=auth_header(token))
        assert r.status_code == 403

    def test_admin_statistics_success(self, client, seed_users):
        """管理员访问统计接口成功"""
        token = login(client, "admin", "123456", "admin")
        r = get_json(client, "/api/admin/statistics", headers=auth_header(token))
        assert r.status_code == 200

    def test_admin_users_list_success(self, client, seed_users):
        """管理员获取用户列表"""
        token = login(client, "admin", "123456", "admin")
        r = get_json(client, "/api/admin/users", headers=auth_header(token))
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert "items" in data

    def test_admin_logs_success(self, client, seed_users):
        """管理员获取系统日志"""
        token = login(client, "admin", "123456", "admin")
        r = get_json(client, "/api/admin/logs", headers=auth_header(token))
        assert r.status_code == 200


# ============================================================
# 六、健康检查
# ============================================================

class TestHealth:
    """健康检查端点测试"""

    def test_liveness(self, client):
        """存活探针"""
        r = get_json(client, "/api/health/live")
        assert r.status_code == 200
        data = r.get_json()
        assert data["alive"] is True
