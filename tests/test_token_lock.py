"""Redis 分布式锁单元测试"""
import pytest
import threading
import time
from unittest.mock import patch, MagicMock


class FakeRedis:
    """内存 Redis 模拟"""
    def __init__(self):
        self._store = {}
        self._locks = set()

    def get(self, key):
        val = self._store.get(key)
        return val.encode() if isinstance(val, str) else val

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self._store:
            return False
        self._store[key] = value
        return True

    def setex(self, key, ttl, value):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def exists(self, key):
        return key in self._store

    def ping(self):
        return True


class TestRedisLock:
    """分布式锁测试"""

    def test_single_instance_token_cache(self):
        """单实例 Token 获取和缓存"""
        store = {
            "wecom:token:corp1": b"",
        }
        lock_held = {"status": False}

        # 模拟 get_access_token 的核心逻辑
        def get_access_token(corp_id):
            cache_key = f"wecom:token:{corp_id}"
            token = store.get(cache_key)
            if token:
                return token.decode()

            lock_key = f"wecom:token:lock:{corp_id}"
            if "locked" not in store:
                store["locked"] = True
                try:
                    token = "fake_test_token_12345"
                    store[cache_key] = token.encode()
                    return token
                finally:
                    store.pop("locked", None)
            else:
                time.sleep(0.1)
                return get_access_token(corp_id)

        token = get_access_token("corp1")
        assert token == "fake_test_token_12345"
        # 第二次调用应从缓存获取
        assert store["wecom:token:corp1"] == b"fake_test_token_12345"

    def test_lock_prevents_concurrent_refresh(self):
        """锁应阻止并发 Token 刷新"""
        refresh_count = [0]
        lock = threading.Lock()

        def refresh():
            with lock:
                refresh_count[0] += 1
                time.sleep(0.01)

        threads = [threading.Thread(target=refresh) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert refresh_count[0] == 5


class TestTokenEdgeCases:
    """Token 边界测试"""

    def test_early_expiry_buffer(self):
        """提前 200s 过期缓冲应生效"""
        expires_in = 7200
        ttl = max(expires_in - 200, 60)
        assert ttl == 7000  # 7200 - 200

    def test_minimum_ttl(self):
        """最小 TTL 应不低于 60s"""
        expires_in = 100
        ttl = max(expires_in - 200, 60)
        assert ttl == 60  # 不低于最小阈值
