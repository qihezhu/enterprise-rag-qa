"""pytest 共享 fixtures - 企业级测试配置

设计原则：
1. 环境变量在 import server.app 之前设置，确保即使有顶层创建也用 SQLite
2. TestConfig 完全隔离，不依赖任何外部服务（MySQL/Redis/企微/百炼）
3. 每个 fixture 独立，测试间无状态污染
"""
import os

# ==================== 关键：在 import server.app 之前设置环境变量 ====================
# 即使 app.py 有延迟创建，Config 类读取 os.environ 也需要这些值
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("WECOM_SECRET", "test_secret")
os.environ.setdefault("WECOM_CONTACT_SECRET", "test_secret")
os.environ.setdefault("DASHSCOPE_API_KEY", "")
os.environ.setdefault("BAILIAN_APP_ID", "")

import pytest
import fakeredis
from server.app import create_app
from server.config import Config
from server.extensions import db, redis_client


class TestConfig(Config):
    """测试配置 - 完全隔离的测试环境"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    REDIS_URL = "redis://localhost:6379/15"
    WECOM_CORP_ID = "test_corp"
    WECOM_SECRET = "test_secret"
    WECOM_AGENT_ID = "1000001"
    WECOM_TOKEN = "test_token"
    WECOM_ENCODING_AES_KEY = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFG"
    QWEN_TOOL_API_KEY = "test_api_key"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "test_uploads")
    CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(__file__), "test_chroma")


@pytest.fixture
def app():
    """每个测试函数独立的应用实例"""
    app = create_app(TestConfig)
    # 替换 Redis 为 fakeredis，避免依赖真实 Redis
    faker = fakeredis.FakeRedis()
    import server.extensions as ext
    ext.redis_client = faker
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
