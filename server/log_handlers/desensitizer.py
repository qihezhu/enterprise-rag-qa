"""
日志脱敏中间件
对敏感信息（手机号、身份证、Secret/Token）在落盘前进行掩码处理
"""
import re
import logging


# 脱敏规则
_PATTERNS = [
    # 手机号: 138****1234
    (re.compile(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)"), r"\1****\2"),
    # 身份证: 110***********1234
    (re.compile(r"(?<!\d)(\d{3})\d{12}(\d{3}[\dXx])(?!\d)"), r"\1***********\2"),
    # 企微 Secret 格式: 任意长字符串在 key=secret 上下文中
    (re.compile(r"(corpsecret|secret|Secret)\s*[:=]\s*['\"]?([^&\s'\"]{8,})['\"]?"), r"\1:***REDACTED***"),
    # access_token
    (re.compile(r"(access_token|token)\s*[:=]\s*['\"]?([^&\s'\"]{8,})['\"]?"), r"\1:***REDACTED***"),
]


def desensitize(text):
    """对文本中的敏感信息进行脱敏"""
    if not isinstance(text, str):
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class DesensitizingFormatter(logging.Formatter):
    """带脱敏功能的日志格式化器"""

    def format(self, record):
        original = super().format(record)
        return desensitize(original)


def register_desensitization(app):
    """注册日志脱敏：为所有 Flask handler 设置脱敏格式化器"""
    formatter = DesensitizingFormatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)
    # 同时为 werkzeug 访问日志脱敏
    werkzeug_logger = logging.getLogger("werkzeug")
    for handler in werkzeug_logger.handlers:
        handler.setFormatter(formatter)
