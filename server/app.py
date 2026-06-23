"""
Flask应用入口模块
创建Flask应用实例，注册所有蓝图和扩展，提供应用工厂函数
"""
import os
import logging
import redis as redis_lib
from flask import Flask
from .config import Config
from . import extensions as _ext
from .extensions import db, cors


def create_app(config_class=Config):
    """
    应用工厂函数：创建并配置Flask应用实例
    参数：
        config_class: 配置类，默认使用Config
    返回：
        配置完成的Flask应用对象
    """
    app = Flask(__name__)

    # 加载配置
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    cors.init_app(app, supports_credentials=True)

    # 初始化 Redis
    _ext.redis_client = redis_lib.from_url(app.config["REDIS_URL"])

    # 确保上传目录和Chroma持久化目录存在
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["CHROMA_PERSIST_DIR"], exist_ok=True)

    # ==================== 初始化企微客户端 ====================
    from .clients.wecom_client import wecom_client
    wecom_client.init_app(app)

    # ==================== 初始化百炼 Agent 客户端 ====================
    from .clients.bailian_client import bailian_client
    bailian_client.init_app(app)

    # ==================== 注册蓝图 ====================
    from .routes.auth import auth_bp
    from .routes.document import doc_bp
    from .routes.qa import qa_bp
    from .routes.admin import admin_bp
    from .routes.wecom import wecom_bp
    from .routes.tools.approval_tool import tool_bp
    from .routes.tools import contact_tool   # 注册联系人 Tool 路由
    from .routes.tools import calendar_tool  # 注册日程 Tool 路由
    from .routes.tools import customer_tool  # 注册客户运营 Tool 路由
    from .routes.tools import rag_tool       # 注册知识库 RAG Tool 路由

    app.register_blueprint(auth_bp)     # /api/auth/*
    app.register_blueprint(doc_bp)      # /api/documents/*
    app.register_blueprint(qa_bp)       # /api/qa/*
    app.register_blueprint(admin_bp)    # /api/admin/*
    app.register_blueprint(wecom_bp)    # /api/wecom/*
    app.register_blueprint(tool_bp)     # /api/tools/*

    # 注册健康检查蓝图
    from .monitoring.health import health_bp
    app.register_blueprint(health_bp)   # /api/health/*

    # ==================== 初始化审计日志 ====================
    from .log_handlers.audit_logger import audit_log
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] AUDIT %(message)s"
    ))
    audit_log.addHandler(audit_handler)
    audit_log.setLevel(logging.INFO)
    audit_log.propagate = False

    # ==================== 注册日志脱敏 ====================
    from .log_handlers.desensitizer import register_desensitization
    register_desensitization(app)

    # ==================== 创建数据库表 ====================
    with app.app_context():
        db.create_all()

    return app


# 创建应用实例（供 flask run 或 python app.py 直接运行使用）
app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
