"""
标签缓存服务
Redis 缓存企业标签列表，TTL=3600，变更前自动刷新
"""
from flask import current_app
from ..clients.wecom_client import wecom_client
from ..extensions import redis_client

CACHE_KEY = "wecom:tag_list"
CACHE_TTL = 3600  # 1 小时


def _redis_ok():
    try:
        return redis_client is not None and redis_client.ping()
    except Exception:
        return False


class TagCacheService:
    """企业标签缓存 —— 避免频繁调 API 获取标签列表"""

    def __init__(self):
        self._mem_cache = None

    def get_tags(self):
        """获取标签列表（缓存优先，过期自动刷新）"""
        if _redis_ok():
            cached = redis_client.get(CACHE_KEY)
            if cached:
                import json
                return json.loads(cached)
        elif self._mem_cache is not None:
            return self._mem_cache

        return self.refresh_tags()

    def refresh_tags(self):
        """强制刷新标签缓存"""
        resp = wecom_client.get_corp_tag_list()
        if resp.get("errcode") != 0:
            current_app.logger.warning(f"[标签缓存] 刷新失败: {resp.get('errmsg')}")
            return []

        tags = self._flatten_tags(resp.get("tag_group", []))
        import json
        if _redis_ok():
            redis_client.setex(CACHE_KEY, CACHE_TTL, json.dumps(tags, ensure_ascii=False))
        else:
            self._mem_cache = tags
        current_app.logger.info(f"[标签缓存] 已刷新 {len(tags)} 个标签")
        return tags

    def resolve_tag_ids(self, tag_names):
        """将标签名称列表解析为标签 ID 列表（API不可用时用名称作为Demo ID）"""
        self.refresh_tags()
        tags = self.get_tags()
        result = []
        for name in tag_names:
            for tag in tags:
                if tag.get("name") == name:
                    result.append(tag.get("id", ""))
                    break
            else:
                # API无数据时降级：用标签名本身作为demo ID
                result.append(f"DEMO-TAG-{name}")
        return result

    def _flatten_tags(self, tag_groups):
        """将标签组扁平化为标签列表"""
        result = []
        for group in tag_groups:
            group_name = group.get("group_name", "")
            for tag in group.get("tag", []):
                result.append({
                    "id": tag.get("id", ""),
                    "name": tag.get("name", ""),
                    "group_name": group_name,
                })
        return result


tag_cache = TagCacheService()
