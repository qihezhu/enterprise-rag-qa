"""
内存指标收集器
记录 Tool 调用量、成功率、P50/P95/P99 延迟，供管理端查询
"""
import time
import threading
from collections import defaultdict

# 内存指标存储
_lock = threading.Lock()
_call_counts = defaultdict(int)
_call_success = defaultdict(int)
_call_errors = defaultdict(int)
_call_latencies = defaultdict(list)  # 保留最近 1000 条延迟


MAX_LATENCIES = 1000


def record_tool_call(tool_name, duration_ms, success=True):
    """记录一次 Tool 调用"""
    with _lock:
        _call_counts[tool_name] += 1
        if success:
            _call_success[tool_name] += 1
        else:
            _call_errors[tool_name] += 1
        latencies = _call_latencies[tool_name]
        latencies.append(duration_ms)
        if len(latencies) > MAX_LATENCIES:
            _call_latencies[tool_name] = latencies[-MAX_LATENCIES:]


def get_metrics():
    """获取所有指标快照"""
    with _lock:
        result = {}
        all_tools = set(_call_counts.keys()) | set(_call_success.keys()) | set(_call_errors.keys())
        for tool in all_tools:
            total = _call_counts.get(tool, 0)
            success = _call_success.get(tool, 0)
            errors = _call_errors.get(tool, 0)
            latencies = sorted(_call_latencies.get(tool, []))
            result[tool] = {
                "calls": total,
                "success": success,
                "errors": errors,
                "success_rate": round(success / total * 100, 1) if total > 0 else 0,
                "p50_ms": _percentile(latencies, 50),
                "p95_ms": _percentile(latencies, 95),
                "p99_ms": _percentile(latencies, 99),
            }
        return result


def _percentile(sorted_data, p):
    """计算百分位数"""
    if not sorted_data:
        return 0
    idx = int(len(sorted_data) * p / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]


# ==================== Tool 调用装饰器 ====================

def track_tool_metrics(tool_name):
    """装饰器：自动记录 Tool 调用的耗时和成功率"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            success = True
            try:
                return func(*args, **kwargs)
            except Exception:
                success = False
                raise
            finally:
                duration_ms = (time.time() - start) * 1000
                record_tool_call(tool_name, duration_ms, success)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
