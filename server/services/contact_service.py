"""
智能组织大脑服务
自然语言查人、查部门、查汇报线，输出前脱敏
"""
import re
import os
import json
from flask import current_app
from ..clients.wecom_client import wecom_client


class ContactService:
    """组织大脑 —— 通讯录智能搜索"""

    def __init__(self):
        self._name_cache = {}   # name_lower → userid
        self._cache_loaded = False
        self._dept_map = None   # dept_id → dept_name

    def _load_cache(self):
        if self._cache_loaded:
            return
        try:
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'name_cache.json')
            with open(cache_path, 'r', encoding='utf-8') as f:
                self._name_cache = json.load(f)
        except Exception:
            pass
        self._cache_loaded = True

    def _save_cache(self):
        try:
            cache_path = os.path.join(os.path.dirname(__file__), '..', 'name_cache.json')
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._name_cache, f, ensure_ascii=False)
        except Exception:
            pass

    def register_user(self, userid):
        """根据 userid 查找姓名并注册到缓存（供消息回调使用）"""
        detail = wecom_client.get_user_detail(userid)
        if detail.get("errcode") == 0:
            name = detail.get("name", "")
            if name:
                self._load_cache()
                self._name_cache[name.lower()] = userid
                self._save_cache()

    def search_user(self, query):
        """
        搜索成员（支持姓名、手机号、拼音、userid）
        返回脱敏后的成员信息列表
        """
        self._load_cache()
        results = []
        query_clean = query.strip()

        # 判断输入是否为手机号
        if re.match(r"^1[3-9]\d{9}$", query_clean):
            resp = wecom_client.userid_by_mobile(query_clean)
            if resp.get("errcode") == 0 and resp.get("userid"):
                detail = wecom_client.get_user_detail(resp["userid"])
                if detail.get("errcode") == 0:
                    results = [self._format_user(detail)]
                    return {"results": results, "total": len(results)}
            return {"results": [], "total": 0}

        # 1. 检查 name→userid 缓存
        cached_uid = self._name_cache.get(query_clean.lower())
        if cached_uid:
            detail = wecom_client.get_user_detail(cached_uid)
            if detail.get("errcode") == 0:
                results.append(self._format_user(detail))

        # 2. 直接作为 userid 查询
        seen_ids = {r["userid"] for r in results}
        detail = wecom_client.get_user_detail(query_clean)
        if detail.get("errcode") == 0:
            formatted = self._format_user(detail)
            if formatted["userid"] not in seen_ids:
                results.append(formatted)
                seen_ids.add(formatted["userid"])
            name = detail.get("name", "")
            if name and name.lower() not in self._name_cache:
                self._name_cache[name.lower()] = query_clean
                self._save_cache()

        # 3. 中文名 → 拼音 userid 候选
        if not results and self._contains_chinese(query_clean):
            for candidate in self._userid_candidates(query_clean):
                if candidate.lower() == query_clean.lower():
                    continue
                d = wecom_client.get_user_detail(candidate)
                if d.get("errcode") == 0:
                    formatted = self._format_user(d)
                    if formatted["userid"] not in seen_ids:
                        results.append(formatted)
                        seen_ids.add(formatted["userid"])
                    name = d.get("name", "")
                    if name and name.lower() not in self._name_cache:
                        self._name_cache[name.lower()] = candidate
                        self._save_cache()
                    break

        # 4. 按姓名搜索：遍历部门获取匹配成员
        dept_list = self._get_all_departments()
        for dept in dept_list:
            dept_users = self._get_department_users(dept.get("id", 0))
            for user in dept_users:
                uid = user.get("userid", "")
                if uid in seen_ids:
                    continue
                name = user.get("name", "")
                if query_clean.lower() in name.lower():
                    detail = wecom_client.get_user_detail(uid)
                    if detail.get("errcode") == 0:
                        formatted = self._format_user(detail)
                        if formatted["userid"] not in seen_ids:
                            seen_ids.add(formatted["userid"])
                            results.append(formatted)
                    if len(results) >= 20:
                        break
            if len(results) >= 20:
                break

        return {"results": results, "total": len(results)}

    def _contains_chinese(self, s):
        return any('一' <= c <= '鿿' for c in s)

    def _userid_candidates(self, chinese_name):
        """由中文名生成可能的拼音 userid 候选"""
        from pypinyin import pinyin, Style
        syllables = pinyin(chinese_name, style=Style.NORMAL)
        seen = set()
        candidates = []
        # 全拼小写: xuqi
        full = ''.join([s[0] for s in syllables])
        if full not in seen:
            seen.add(full); candidates.append(full)
        # 全拼大写: XUQI
        if full.upper() not in seen:
            seen.add(full.upper()); candidates.append(full.upper())
        # 首字母大写: Xuqi
        if full.capitalize() not in seen:
            seen.add(full.capitalize()); candidates.append(full.capitalize())
        # PascalCase: XuQi
        pascal = ''.join([s[0].capitalize() for s in syllables])
        if pascal not in seen:
            seen.add(pascal); candidates.append(pascal)
        return candidates

    def get_department_members(self, dept_id, recursive=True):
        """获取部门成员列表（支持递归子部门），自动补全详细信息"""
        members = self._get_department_users(dept_id)
        result = [self._enrich_and_format(m) for m in members]

        if recursive:
            dept_list = self._get_all_departments()
            child_depts = [d for d in dept_list if d.get("parentid") == dept_id]
            for child in child_depts:
                child_members = self._get_department_users(child.get("id", 0))
                result.extend([self._enrich_and_format(m) for m in child_members])

        return {"dept_id": dept_id, "members": result, "total": len(result)}

    def _enrich_and_format(self, user):
        """从 list_user_simple 的摘要数据补全为完整用户信息（含状态、手机号等）"""
        uid = user.get("userid", "")
        if uid:
            detail = wecom_client.get_user_detail(uid)
            if detail.get("errcode") == 0:
                return self._format_user(detail)
        return self._format_user(user)

    def get_report_chain(self, user_id):
        """获取汇报链（向上遍历部门层级，支持 name/userid/手机号）"""
        detail = wecom_client.get_user_detail(user_id)
        if detail.get("errcode") != 0:
            # 查询失败时尝试姓名搜索
            search = self.search_user(user_id)
            if search.get("total", 0) > 0:
                resolved = search["results"][0]["userid"]
                detail = wecom_client.get_user_detail(resolved)
        if detail.get("errcode") != 0:
            return {"user_id": user_id, "chain": [], "error": detail.get("errmsg")}

        resolved_uid = detail.get("userid", user_id)
        chain = [self._format_user(detail)]
        chain_uids = {resolved_uid}
        current_dept_ids = detail.get("department", [])
        visited = set()

        # 向上遍历部门层级（最多 10 层）
        for _ in range(10):
            if not current_dept_ids:
                break
            dept_list = self._get_all_departments()
            parent_ids = []
            for dept_id in current_dept_ids:
                if dept_id in visited:
                    continue
                visited.add(dept_id)
                dept = next((d for d in dept_list if d.get("id") == dept_id), None)
                if dept and dept.get("parentid") and dept["parentid"] != 0:
                    parent_ids.append(dept["parentid"])
                    leader = self._get_dept_leader(dept_id)
                    if leader and leader["userid"] not in chain_uids:
                        chain_uids.add(leader["userid"])
                        chain.append(leader)
            current_dept_ids = parent_ids

        return {"user_id": resolved_uid, "chain": chain}

    # ==================== 内部辅助 ====================

    def _format_user(self, user_data):
        """格式化用户信息并脱敏"""
        dept_ids = user_data.get("department", [])
        if isinstance(dept_ids, list) and dept_ids:
            dept_names = [self._dept_id_to_name(d) for d in dept_ids]
            dept_str = ", ".join(dept_names)
        else:
            dept_str = str(dept_ids) if dept_ids else ""
        # 状态字段：list_user_simple 不返回 status，此时默认为"在职"（部门列表仅包含在职成员）
        status_raw = user_data.get("status")
        if status_raw is None:
            status_str = "在职"
        else:
            status_str = "在职" if status_raw == 1 else "离职"
        return {
            "userid": user_data.get("userid", ""),
            "name": user_data.get("name", ""),
            "department": dept_str,
            "position": user_data.get("position", ""),
            "mobile": _desensitize_phone(user_data.get("mobile", "")),
            "email": user_data.get("email", ""),
            "status": status_str,
        }

    def _dept_id_to_name(self, dept_id):
        if self._dept_map is None:
            self._dept_map = {}
            for d in self._get_all_departments():
                self._dept_map[d.get("id")] = d.get("name", str(d.get("id")))
        return self._dept_map.get(dept_id, str(dept_id))

    def _get_all_departments(self):
        """获取全量部门列表"""
        resp = wecom_client.list_department(0)
        if resp.get("errcode") != 0:
            return []
        return resp.get("department", [])

    def _get_department_users(self, dept_id):
        """获取指定部门的成员（简单模式）"""
        try:
            resp = wecom_client.list_user_simple(dept_id, fetch_child=0)
            if resp.get("errcode") == 0:
                return resp.get("userlist", [])
        except Exception:
            pass
        return []

    def _get_dept_leader(self, dept_id):
        """获取部门负责人"""
        try:
            resp = wecom_client.list_user(dept_id, fetch_child=0)
            if resp.get("errcode") == 0:
                for user in resp.get("userlist", []):
                    if user.get("isleader") == 1:
                        return self._format_user(user)
        except Exception:
            pass


def _desensitize_phone(phone):
    """手机号脱敏: 138****1234"""
    if not phone:
        return ""
    p = str(phone)
    if re.match(r"^1[3-9]\d{9}$", p):
        return f"{p[:3]}****{p[-4:]}"
    return p


contact_service = ContactService()
