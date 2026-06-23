"""
Flask扩展初始化模块
集中管理SQLAlchemy、CORS等第三方扩展，避免循环引用
"""
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# 数据库ORM扩展
db = SQLAlchemy()

# CORS跨域扩展
cors = CORS()

# Redis客户端（懒初始化，在 create_app 中赋值）
redis_client = None
