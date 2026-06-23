"""
P0 验收脚本：验证企微 Token 获取和 Redis 缓存
用法: python -m server.clients.test_token
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import redis
from server.config import Config
from server.clients.wecom_client import WeComClient


def main():
    config = Config()
    print("=" * 60)
    print("P0 企微 Token 验证")
    print("=" * 60)
    print(f"  CorpID:      {config.WECOM_CORP_ID or '(未配置)'}")
    print(f"  AgentID:     {config.WECOM_AGENT_ID or '(未配置)'}")
    print(f"  Secret:      {'***已配置***' if config.WECOM_SECRET else '(未配置)'}")
    print(f"  Redis URL:   {config.REDIS_URL}")
    print()

    if not config.WECOM_CORP_ID or not config.WECOM_SECRET:
        print("[错误] 请先设置环境变量 WECOM_CORP_ID 和 WECOM_SECRET")
        sys.exit(1)

    # 初始化 Redis
    r = redis.from_url(config.REDIS_URL)
    try:
        r.ping()
        print("[Redis] 连接成功")
    except Exception as e:
        print(f"[Redis] 连接失败: {e}")
        sys.exit(1)

    # 初始化 WeComClient（手动注入依赖）
    client = WeComClient()
    client._corp_id = config.WECOM_CORP_ID
    client._secret = config.WECOM_SECRET
    client._agent_id = config.WECOM_AGENT_ID
    client._api_base = config.WECOM_API_BASE

    # 将 Redis 注入到 extensions 模块
    import server.extensions as ext
    ext.redis_client = r

    # 测试获取 Token
    print("\n[测试] 获取 access_token...")
    try:
        token = client.get_access_token()
        print(f"[成功] Token 获取成功: {token[:10]}...{token[-10:]}")
    except Exception as e:
        print(f"[失败] Token 获取失败: {e}")
        sys.exit(1)

    # 验证 Redis 缓存
    cache_key = f"wecom:token:{config.WECOM_CORP_ID}"
    cached = r.get(cache_key)
    if cached:
        print(f"[成功] Token 已缓存至 Redis, key={cache_key}")
    else:
        print("[警告] Token 未在 Redis 中找到缓存")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("P0 验收通过: Token 获取 + Redis 缓存均正常")
    print("=" * 60)


if __name__ == "__main__":
    main()
