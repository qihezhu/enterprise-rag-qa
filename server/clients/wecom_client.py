"""
企业微信开放平台 API 客户端
封装 Token 管理（Redis分布式锁 + 提前过期）、所有 API 调用
"""
import time
import requests
from flask import current_app
from ..extensions import redis_client


class WeComClient:
    """企业微信 API 客户端，单例模式"""

    TOKEN_URL = "/cgi-bin/gettoken"

    def __init__(self, app=None):
        self._corp_id = None
        self._secret = None
        self._contact_secret = None
        self._agent_id = None
        self._api_base = None
        self._token_cache = {}   # 内存缓存 fallback：{token: expiry_timestamp}
        if app:
            self.init_app(app)

    def init_app(self, app):
        self._corp_id = app.config["WECOM_CORP_ID"]
        self._secret = app.config["WECOM_SECRET"]
        self._contact_secret = app.config.get("WECOM_CONTACT_SECRET", "")
        self._agent_id = app.config["WECOM_AGENT_ID"]
        self._api_base = app.config["WECOM_API_BASE"]

    # ==================== Token 管理 ====================

    def _redis_ok(self):
        try:
            return redis_client is not None and redis_client.ping()
        except Exception:
            return False

    def get_access_token(self):
        """
        获取 access_token（Redis分布式锁 + 提前200s过期，Redis不可用时降级为内存缓存）
        """
        cache_key = f"wecom:token:{self._corp_id}"

        if self._redis_ok():
            token = redis_client.get(cache_key)
            if token:
                return token.decode("utf-8")

            lock_key = f"wecom:token:lock:{self._corp_id}"
            if redis_client.set(lock_key, "1", nx=True, ex=5):
                try:
                    return self._fetch_and_cache_token(cache_key, lock_key)
                finally:
                    redis_client.delete(lock_key)
            else:
                time.sleep(1)
                return self.get_access_token()
        else:
            # Redis 不可用，降级为内存缓存
            entry = self._token_cache.get(cache_key)
            if entry and time.time() < entry["expires_at"]:
                return entry["token"]
            return self._fetch_and_cache_token_memory(cache_key)

    def _fetch_and_cache_token(self, cache_key, lock_key=None):
        url = f"{self._api_base}{self.TOKEN_URL}"
        resp = requests.get(
            url,
            params={"corpid": self._corp_id, "corpsecret": self._secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取Token失败: {data.get('errmsg', '未知错误')}")
        token = data["access_token"]
        expires_in = data.get("expires_in", 7200)
        ttl = max(expires_in - 200, 60)
        redis_client.setex(cache_key, ttl, token)
        return token

    def get_contact_token(self):
        """获取通讯录专用 access_token（使用通讯录同步Secret）"""
        if not self._contact_secret:
            return self.get_access_token()  # fallback 到应用 token
        cache_key = f"wecom:token:contact:{self._corp_id}"
        if self._redis_ok():
            token = redis_client.get(cache_key)
            if token:
                return token.decode("utf-8")
            lock_key = f"wecom:token:lock:contact:{self._corp_id}"
            if redis_client.set(lock_key, "1", nx=True, ex=5):
                try:
                    return self._fetch_and_cache_contact_token(cache_key, lock_key)
                finally:
                    redis_client.delete(lock_key)
            else:
                time.sleep(1)
                return self.get_contact_token()
        else:
            entry = self._token_cache.get(cache_key)
            if entry and time.time() < entry["expires_at"]:
                return entry["token"]
            return self._fetch_and_cache_contact_token_memory(cache_key)

    def _fetch_and_cache_contact_token(self, cache_key, lock_key=None):
        url = f"{self._api_base}{self.TOKEN_URL}"
        resp = requests.get(url, params={"corpid": self._corp_id, "corpsecret": self._contact_secret}, timeout=10)
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取通讯录Token失败: {data.get('errmsg', '未知错误')}")
        token = data["access_token"]
        ttl = max(data.get("expires_in", 7200) - 200, 60)
        redis_client.setex(cache_key, ttl, token)
        return token

    def _fetch_and_cache_contact_token_memory(self, cache_key):
        url = f"{self._api_base}{self.TOKEN_URL}"
        resp = requests.get(url, params={"corpid": self._corp_id, "corpsecret": self._contact_secret}, timeout=10)
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取通讯录Token失败: {data.get('errmsg', '未知错误')}")
        token = data["access_token"]
        ttl = max(data.get("expires_in", 7200) - 200, 60)
        self._token_cache[cache_key] = {"token": token, "expires_at": time.time() + ttl}
        return token

    def _fetch_and_cache_token_memory(self, cache_key):
        url = f"{self._api_base}{self.TOKEN_URL}"
        resp = requests.get(
            url,
            params={"corpid": self._corp_id, "corpsecret": self._secret},
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"获取Token失败: {data.get('errmsg', '未知错误')}")
        token = data["access_token"]
        expires_in = data.get("expires_in", 7200)
        ttl = max(expires_in - 200, 60)
        self._token_cache[cache_key] = {
            "token": token,
            "expires_at": time.time() + ttl,
        }
        return token

    # ==================== 通用请求 ====================

    def _request(self, method, path, **kwargs):
        """带 Token 注入和重试的通用请求"""
        return self._do_request(method, path, self.get_access_token, "wecom:token", **kwargs)

    def _request_contact(self, method, path, **kwargs):
        """带通讯录Token的通用请求"""
        return self._do_request(method, path, self.get_contact_token, "wecom:token:contact", **kwargs)

    def _do_request(self, method, path, get_token_fn, token_key, **kwargs):
        token = get_token_fn()
        url = f"{self._api_base}{path}"
        params = kwargs.pop("params", {})
        params["access_token"] = token
        timeout = kwargs.pop("timeout", 15)

        for attempt in range(3):
            try:
                resp = requests.request(
                    method, url, params=params, timeout=timeout, **kwargs
                )
                try:
                    data = resp.json()
                except ValueError:
                    data = {"errcode": -1, "errmsg": f"non-JSON response: {resp.text[:200]}"}
                errcode = data.get("errcode", 0)
                if errcode in (40014, 42001):
                    redis_client.delete(f"{token_key}:{self._corp_id}")
                    token = get_token_fn()
                    params["access_token"] = token
                    continue
                return data
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(1)
        return {"errcode": -1, "errmsg": "max retries exceeded"}

    # ==================== 消息与交互 API ====================

    def send_message(self, touser, msg_type, content, safe=0):
        """
        发送应用消息
        支持 text（文本）、template_card（模板卡片）
        """
        body = {
            "touser": touser,
            "msgtype": msg_type,
            "agentid": int(self._agent_id),
            "safe": safe,
        }
        if msg_type == "text":
            body["text"] = {"content": content}
        elif msg_type == "template_card":
            body["template_card"] = content
        return self._request("POST", "/cgi-bin/message/send", json=body)

    def update_button(self, userid, response_code, button_key, replace_text=None):
        """更新卡片按钮状态（防重复点击）"""
        body = {
            "userids": [userid],
            "agentid": int(self._agent_id),
            "response_code": response_code,
            "button": {"replace_name": replace_text or "已处理", "key": button_key},
        }
        return self._request("POST", "/cgi-bin/message/update_template_card", json=body)

    def recall_message(self, msgid):
        """撤回消息（24h内有效）"""
        return self._request("POST", "/cgi-bin/message/recall", json={"msgid": msgid})

    # ==================== 审批 API ====================

    def get_template_detail(self, template_id):
        """获取审批模板详情（动态获取控件ID）"""
        return self._request("POST", "/cgi-bin/oa/gettemplatedetail", json={"template_id": template_id})

    def apply_event(self, approval_data):
        """提交审批申请"""
        return self._request("POST", "/cgi-bin/oa/applyevent", json=approval_data)

    def get_approval_detail(self, sp_no):
        """获取审批单详情"""
        return self._request("POST", "/cgi-bin/oa/getapprovaldetail", json={"sp_no": sp_no})

    def get_approval_info(self, start_time, end_time, cursor=0, size=100):
        """批量获取审批单号"""
        return self._request(
            "POST",
            "/cgi-bin/oa/getapprovalinfo",
            json={"starttime": start_time, "endtime": end_time, "cursor": cursor, "size": size},
        )

    # ==================== 通讯录 API ====================

    def userid_by_mobile(self, mobile):
        """手机号 → userid"""
        return self._request("POST", "/cgi-bin/user/getuserid", json={"mobile": mobile})

    def get_user_detail(self, userid):
        """获取成员详情"""
        return self._request("GET", f"/cgi-bin/user/get", params={"userid": userid})

    def list_department(self, dept_id=0):
        """获取部门列表"""
        return self._request("GET", "/cgi-bin/department/list", params={"id": dept_id})

    def list_user_simple(self, dept_id, fetch_child=0):
        """获取部门成员（简单列表）"""
        return self._request("GET", "/cgi-bin/user/simplelist", params={
            "department_id": dept_id, "fetch_child": fetch_child,
        })

    def list_user(self, dept_id, fetch_child=0):
        """获取部门成员（详情列表）"""
        return self._request("GET", "/cgi-bin/user/list", params={
            "department_id": dept_id, "fetch_child": fetch_child,
        })

    # ==================== 客户联系 API ====================

    def get_external_contact(self, external_userid):
        """获取外部联系人详情"""
        return self._request("GET", "/cgi-bin/externalcontact/get", params={"external_userid": external_userid})

    def list_external_contacts(self, user_id):
        """获取指定成员的外部联系人列表"""
        return self._request("GET", "/cgi-bin/externalcontact/list", params={"userid": user_id})

    def mark_tag(self, userid, external_userid, add_tag=None, remove_tag=None):
        """为客户打标签"""
        body = {"userid": userid, "external_userid": external_userid}
        if add_tag:
            body["add_tag"] = add_tag
        if remove_tag:
            body["remove_tag"] = remove_tag
        return self._request("POST", "/cgi-bin/externalcontact/mark_tag", json=body)

    def get_corp_tag_list(self, tag_id=None):
        """获取企业标签列表"""
        body = {}
        if tag_id:
            body["tag_id"] = tag_id
        return self._request("POST", "/cgi-bin/externalcontact/get_corp_tag_list", json=body)

    def add_msg_template(self, userid, external_userid, text):
        """创建群发任务"""
        body = {
            "chat_type": "single",
            "external_userid": [external_userid],
            "sender": userid,
            "text": {"content": text},
        }
        return self._request("POST", "/cgi-bin/externalcontact/add_msg_template", json=body)

    # ==================== 日程 API ====================

    def get_calendar(self):
        """获取日历列表"""
        return self._request("POST", "/cgi-bin/oa/calendar/get", json={})

    def check_schedule(self, userids, start_time, end_time):
        """查询忙闲状态"""
        body = {"userid_list": userids, "starttime": start_time, "endtime": end_time}
        return self._request("POST", "/cgi-bin/oa/schedule/get", json=body)

    def add_schedule(self, schedule_data):
        """创建日程"""
        return self._request("POST", "/cgi-bin/oa/schedule/add", json={"schedule": schedule_data})


# 全局单例
wecom_client = WeComClient()
