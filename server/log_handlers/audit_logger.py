"""
结构化审计日志
记录所有 Tool 调用：时间戳、调用方、用户、操作、结果、延迟
"""
import time
import json
import logging
from functools import wraps
from flask import request

audit_log = logging.getLogger("audit")


def log_tool_call(tool_name, user_id, action, result, latency_ms, extra=None):
    """记录一次 Tool 调用到审计日志"""
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tool": tool_name,
        "user_id": user_id,
        "action": action,
        "result": "success" if result else "failure",
        "latency_ms": round(latency_ms, 2),
    }
    if extra:
        entry["extra"] = extra
    audit_log.info(json.dumps(entry, ensure_ascii=False))


def audit_decorator(tool_name):
    """装饰器：自动记录 Tool 调用审计日志"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                data = request.get_json(silent=True) or {}
                user_id = data.get("user_id", "")
                result = func(*args, **kwargs)
                latency_ms = (time.time() - start) * 1000
                log_tool_call(tool_name, user_id, func.__name__, True, latency_ms)
                return result
            except Exception as e:
                latency_ms = (time.time() - start) * 1000
                log_tool_call(tool_name, "", func.__name__, False, latency_ms, {"error": str(e)})
                raise
        return wrapper
    return decorator
