"""
客户运营服务
打标签、创建群发任务、查跟进记录，赋能一线销售
"""
from datetime import datetime, timezone, timedelta
from flask import current_app
from ..clients.wecom_client import wecom_client
from ..extensions import redis_client
from .tag_cache_service import tag_cache

# 群发频率限制：每人每天1条
BROADCAST_LIMIT_KEY = "wecom:broadcast_count:{}:{}"  # user_id:date
CST = timezone(timedelta(hours=8))


def _redis_ok():
    try:
        return redis_client is not None and redis_client.ping()
    except Exception:
        return False


class CustomerService:
    """客户运营工作台"""

    # ==================== 搜索外部联系人 ====================

    def search_external_contact(self, user_id, name):
        """按姓名搜索外部联系人，返回匹配的 external_userid 和详情"""
        try:
            resp = wecom_client.list_external_contacts(user_id)
            if resp.get("errcode") != 0:
                return []
            external_userids = resp.get("external_userid", [])
            results = []
            for eid in external_userids:
                try:
                    detail = wecom_client.get_external_contact(eid)
                    if detail.get("errcode") == 0:
                        contact = detail.get("external_contact", {})
                        contact_name = contact.get("name", "")
                        if name in contact_name or contact_name in name:
                            results.append({
                                "external_userid": eid,
                                "name": contact_name,
                                "position": contact.get("position", ""),
                                "corp_name": contact.get("corp_name", ""),
                                "type": contact.get("type", 1),
                                "gender": "男" if contact.get("gender") == 1 else "女",
                            })
                except Exception:
                    pass
            return results
        except Exception:
            return []

    # ==================== 打标签 ====================

    def mark_tag(self, user_id, external_userid, tag_names):
        """为外部联系人打标签（API不可用时降级为Demo模式）"""
        tag_ids = tag_cache.resolve_tag_ids(tag_names)
        try:
            resp = wecom_client.mark_tag(
                userid=user_id,
                external_userid=external_userid,
                add_tag=tag_ids,
            )
            if resp.get("errcode") == 0:
                return resp
        except Exception:
            pass
        return {"errcode": 0, "demo_mode": True, "tags": tag_names}

    # ==================== 群发任务 ====================

    def create_broadcast(self, user_id, external_userid, text):
        """
        创建群发任务
        本地计数拦截：企微限制每人每天1条，Tool 层做本地计数避免 API 报错
        """
        # 检查今日发送计数
        today = datetime.now(CST).strftime("%Y%m%d")
        count_key = BROADCAST_LIMIT_KEY.format(user_id, today)

        if _redis_ok():
            count = redis_client.get(count_key)
            count = int(count) if count else 0
        else:
            count = getattr(self, '_broadcast_count', 0)

        if count >= 1:
            return {
                "errcode": -1,
                "errmsg": "今日群发次数已用完（每人每天限1条），请明天再试",
                "today_count": count,
            }

        # 创建群发
        try:
            resp = wecom_client.add_msg_template(user_id, external_userid, text)
            if resp.get("errcode") == 0:
                if _redis_ok():
                    redis_client.incr(count_key)
                    redis_client.expire(count_key, 86400)
                else:
                    self._broadcast_count = count + 1
                return resp
        except Exception:
            pass
        return {"errcode": 0, "msgid": f"DEMO-MSG-{today}-{user_id}", "demo_mode": True}

    # ==================== 查跟进记录 ====================

    def get_follow_up(self, external_userid):
        """获取客户跟进信息（API不可用时降级为Demo）"""
        try:
            resp = wecom_client.get_external_contact(external_userid)
            if resp.get("errcode") == 0:
                contact = resp.get("external_contact", {})
                follow_user = resp.get("follow_user", [])
                return {
                    "external_userid": external_userid,
                    "name": contact.get("name", ""),
                    "position": contact.get("position", ""),
                    "corp_name": contact.get("corp_name", ""),
                    "tags": [
                        {"name": t.get("tag_name", ""), "group": t.get("group_name", "")}
                        for u in follow_user
                        for t in u.get("tags", [])
                    ],
                    "follow_users": [
                        {"userid": u.get("userid", ""), "remark": u.get("remark", ""), "add_time": u.get("createtime", 0)}
                        for u in follow_user
                    ],
                }
        except Exception:
            pass
        return {
            "external_userid": external_userid,
            "name": "演示客户",
            "position": "经理",
            "corp_name": "演示公司",
            "tags": [{"name": "VIP客户", "group": "客户等级"}],
            "follow_users": [{"userid": "zhangsan", "remark": "演示跟进人", "add_time": 0}],
        }


customer_service = CustomerService()
