"""pytest 共享 fixtures"""
import pytest
import fakeredis
from server.app import create_app
from server.config import Config
from server.extensions import db, redis_client


class TestConfig(Config):
    """测试配置"""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WECOM_CORP_ID = "test_corp"
    WECOM_SECRET = "test_secret"
    WECOM_AGENT_ID = "1000001"
    WECOM_TOKEN = "test_token"
    WECOM_ENCODING_AES_KEY = "abcdefghijklmnopqrstuvwxyz01234567890ABCDEFG"
    REDIS_URL = "redis://localhost:6379/1"
    QWEN_TOOL_API_KEY = "test_api_key"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    faker = fakeredis.FakeRedis()
    import server.extensions as ext
    ext.redis_client = faker
    app.config.update({"TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
