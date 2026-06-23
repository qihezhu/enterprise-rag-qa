"""
用户模型
映射数据库表 t_user，存储系统用户信息
"""
import hashlib
from datetime import datetime
from ..extensions import db


class User(db.Model):
    """用户模型类，对应t_user表"""

    __tablename__ = "t_user"

    # ==================== 表字段 ====================
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = db.Column(db.String(50), unique=True, nullable=False, comment="用户名")
    password = db.Column(db.String(32), nullable=False, comment="MD5加密密码")
    role = db.Column(db.Enum("admin", "user"), default="user", comment="角色：admin管理员 user普通用户")
    email = db.Column(db.String(100), default=None, comment="邮箱")
    phone = db.Column(db.String(20), default=None, comment="手机号")
    avatar = db.Column(db.String(255), default=None, comment="头像URL")
    status = db.Column(db.SmallInteger, default=1, comment="状态：1启用 0禁用")
    created_at = db.Column(db.DateTime, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # ==================== 关联关系 ====================
    documents = db.relationship("Document", backref="uploader", lazy="dynamic")
    conversations = db.relationship("Conversation", backref="user", lazy="dynamic")

    def to_dict(self):
        """
        将用户对象序列化为字典（不包含密码字段）
        返回：dict
        """
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "email": self.email or "",
            "phone": self.phone or "",
            "avatar": self.avatar or "",
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else "",
        }

    @staticmethod
    def hash_password(raw_password):
        """
        对原始密码进行MD5加密
        参数：
            raw_password: 原始密码字符串
        返回：
            MD5加密后的32位十六进制字符串
        """
        return hashlib.md5(raw_password.encode("utf-8")).hexdigest()

    def check_password(self, raw_password):
        """
        验证密码是否正确
        参数：
            raw_password: 原始密码字符串
        返回：
            bool: 密码是否匹配
        """
        return self.password == self.hash_password(raw_password)

    def is_admin(self):
        """
        判断当前用户是否为管理员
        返回：bool
        """
        return self.role == "admin"

    def is_active(self):
        """
        判断当前用户是否处于启用状态
        返回：bool
        """
        return self.status == 1

    def __repr__(self):
        return f"<User {self.username}>"
