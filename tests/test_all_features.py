"""
全功能自动化测试脚本
覆盖：认证、文档、RAG问答、管理后台、企微回调、15个Tool端点、E2E流程、安全
"""
import json
import urllib.request
import urllib.error
import urllib.parse
import sys
import os
import io

BASE = "http://localhost:5000"
TOOL_HEADERS = {"Content-Type": "application/json", "X-Tool-API-Key": "test_api_key"}

passed = 0
failed = 0
errors = []


def req(method, path, body=None, headers=None):
    """发送 HTTP 请求，返回 (status, response_dict)"""
    # URL 编码中文参数
    if "?" in path:
        base, qs = path.split("?", 1)
        path = base + "?" + urllib.parse.quote(qs, safe="=&")
    url = f"{BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, {"_raw": raw}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw}
    except Exception as e:
        return 0, {"_error": str(e)}


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")
        errors.append(f"{name}: {detail}")


def auth_headers(token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def login(username, password, role):
    return req("POST", "/api/auth/login", {"username": username, "password": password, "role": role})


# ============================================================
print("=" * 60)
print("  一、用户认证与权限")
print("=" * 60)

# 1.1 管理员登录
s, r = login("admin", "123456", "admin")
check("管理员登录", s == 200 and "token" in r.get("data", {}), r.get("message", ""))
admin_token = r.get("data", {}).get("token", "")

# 1.2 普通用户登录
s, r = login("lisi", "123456", "user")
check("普通用户登录", s == 200 and "token" in r.get("data", {}), r.get("message", ""))
user_token = r.get("data", {}).get("token", "")

# 1.3 密码错误
s, r = login("admin", "wrongpassword", "admin")
check("密码错误拒绝", s == 401, r.get("message", ""))

# 1.4 角色越权（普通用户登管理端）
s, r = login("lisi", "123456", "admin")
check("角色越权拒绝", s == 403, r.get("message", ""))

# 1.5 注册新用户
import time
test_user = f"autotest_{int(time.time()) % 100000}"
s, r = req("POST", "/api/auth/register", {"username": test_user, "password": "123456", "email": "auto@test.com"})
check("注册新用户", s == 201, r.get("message", ""))

# 1.6 重复注册
s, r = req("POST", "/api/auth/register", {"username": "admin", "password": "123456"})
check("重复注册拒绝", s == 409, r.get("message", ""))

# 1.7 短密码拒绝
s, r = req("POST", "/api/auth/register", {"username": "shortpw", "password": "12"})
check("短密码拒绝", s == 400, r.get("message", ""))

# 1.8 获取用户信息
s, r = req("GET", "/api/auth/userinfo", headers=auth_headers(admin_token))
check("获取用户信息", s == 200 and r.get("code") == 200, r.get("message", ""))

# 1.9 未登录拒绝
s, r = req("GET", "/api/auth/userinfo")
check("未登录拒绝", s == 401, r.get("message", ""))

# 1.10 过期/伪造Token拒绝
s, r = req("GET", "/api/auth/userinfo", headers=auth_headers("fake_token_12345"))
check("伪造Token拒绝", s == 401, r.get("message", ""))

# 1.11 正常用户登录状态验证
s, r = login("zhaoliu", "123456", "user")
check("普通用户zhaoliu正常登录", s == 200, f"status={s} {r.get('message','')}")

# 1.12 管理员登用户端
s, r = login("admin", "123456", "user")
check("管理员登用户端拒绝", s == 403, r.get("message", ""))


# ============================================================
print("\n" + "=" * 60)
print("  二、知识文档管理")
print("=" * 60)

# 上传测试 TXT 文件
test_content = "公司年假制度：员工入职满1年享5天年假，满3年享10天年假，满5年享15天年假。请假需提前3天申请。"
test_file = os.path.join(os.path.dirname(__file__), "_test_upload.txt")
with open(test_file, "w", encoding="utf-8") as f:
    f.write(test_content)

# 2.1 上传文档 (通过 multipart/form-data 需要特殊处理)
import http.client
import mimetypes

def upload_document(token, filepath, title, topic=""):
    """multipart/form-data 上传"""
    boundary = "----FormBoundary" + os.urandom(8).hex()
    filename = os.path.basename(filepath)
    body_parts = []
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
    body_parts.append(f"Content-Type: text/plain".encode())
    body_parts.append(b"")
    with open(filepath, "rb") as f:
        body_parts.append(f.read())
    body_parts.append(f"--{boundary}".encode())
    body_parts.append(f'Content-Disposition: form-data; name="title"'.encode())
    body_parts.append(b"")
    body_parts.append(title.encode())
    if topic:
        body_parts.append(f"--{boundary}".encode())
        body_parts.append(f'Content-Disposition: form-data; name="topic"'.encode())
        body_parts.append(b"")
        body_parts.append(topic.encode())
    body_parts.append(f"--{boundary}--".encode())
    body = b"\r\n".join(body_parts)

    conn = http.client.HTTPConnection("localhost", 5000, timeout=30)
    conn.request("POST", "/api/documents", body=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    })
    resp = conn.getresponse()
    data = json.loads(resp.read().decode("utf-8"))
    conn.close()
    return resp.status, data

s, r = upload_document(admin_token, test_file, "年假政策", "人力资源")
check("上传 TXT 文档", s == 201 and r.get("code") == 201 and r.get("data", {}).get("chunk_count", 0) > 0,
      f"chunk_count={r.get('data', {}).get('chunk_count', 0)}")
doc_id = r.get("data", {}).get("id", 0)

# 2.2 上传不支持类型
unsupported_file = os.path.join(os.path.dirname(__file__), "_test.exe")
with open(unsupported_file, "wb") as f:
    f.write(b"MZ\x00\x00")
s, r = upload_document(admin_token, unsupported_file, "virus")
check("不支持类型拒绝", s == 400, str(r.get("message", ""))[:80])

# 2.3 文档列表
s, r = req("GET", "/api/documents?page=1&page_size=10", headers=auth_headers(user_token))
check("文档列表", s == 200 and "items" in r.get("data", {}), "")

# 2.4 关键词搜索
s, r = req("GET", "/api/documents?keyword=年假", headers=auth_headers(user_token))
check("关键词搜索", s == 200, "")

# 2.5 主题筛选
s, r = req("GET", "/api/documents?topic=人力资源", headers=auth_headers(user_token))
check("主题筛选", s == 200, "")

# 2.6 文档详情
if doc_id:
    s, r = req("GET", f"/api/documents/{doc_id}", headers=auth_headers(user_token))
    check("文档详情", s == 200 and r.get("data", {}).get("title") == "年假政策", "")

# 2.7 不存在文档
s, r = req("GET", "/api/documents/99999", headers=auth_headers(user_token))
check("不存在文档404", s == 404, "")

# 2.8 主题列表
s, r = req("GET", "/api/documents/topics", headers=auth_headers(user_token))
check("主题列表", s == 200 and isinstance(r.get("data", []), list), "")

# 2.9 更新文档
if doc_id:
    s, r = req("PUT", f"/api/documents/{doc_id}", {"title": "年假政策(更新)", "topic": "行政管理"}, headers=auth_headers(admin_token))
    check("更新文档", s == 200, r.get("message", ""))

# 2.10 普通用户无权上传
s, r = upload_document(user_token, test_file, "test", "")
check("普通用户无权上传", s == 403, r.get("message", ""))


# ============================================================
print("\n" + "=" * 60)
print("  三、RAG 智能问答")
print("=" * 60)

# 3.1 正常提问（应检索到刚上传的年假文档）
s, r = req("POST", "/api/qa/ask", {"question": "公司年假有多少天？"}, headers=auth_headers(user_token))
check("RAG提问(年假)", s == 200 and "answer" in r.get("data", {}),
      f"sources={len(r.get('data', {}).get('sources', []))}")
sources_count = len(r.get("data", {}).get("sources", []))

# 3.2 无匹配提问
s, r = req("POST", "/api/qa/ask", {"question": "火星移民政策是什么？"}, headers=auth_headers(user_token))
check("RAG无匹配问题", s == 200, "")

# 3.3 空问题拒绝
s, r = req("POST", "/api/qa/ask", {"question": ""}, headers=auth_headers(user_token))
check("RAG空问题拒绝", s == 400, "")

# 3.4 超长问题拒绝
s, r = req("POST", "/api/qa/ask", {"question": "x" * 2001}, headers=auth_headers(user_token))
check("RAG超长问题拒绝", s == 400, "")

# 3.5 对话历史
s, r = req("GET", "/api/qa/history?page=1", headers=auth_headers(user_token))
check("对话历史", s == 200 and "items" in r.get("data", {}), "")


# ============================================================
print("\n" + "=" * 60)
print("  四、管理员后台")
print("=" * 60)

# 4.1 仪表盘
s, r = req("GET", "/api/admin/statistics", headers=auth_headers(admin_token))
check("仪表盘统计", s == 200 and "user_count" in r.get("data", {}), "")

# 4.2 用户列表
s, r = req("GET", "/api/admin/users?page=1", headers=auth_headers(admin_token))
check("用户列表", s == 200, "")

# 4.3 用户搜索
s, r = req("GET", "/api/admin/users?keyword=zhang", headers=auth_headers(admin_token))
check("用户搜索", s == 200, "")

# 4.4 修改用户状态
s, r = req("PUT", "/api/admin/users/3", {"status": 0}, headers=auth_headers(admin_token))
check("禁用用户", s == 200, r.get("message", ""))

# 恢复
s, r = req("PUT", "/api/admin/users/3", {"status": 1}, headers=auth_headers(admin_token))

# 4.5 不能改自己角色
s, r = req("PUT", "/api/admin/users/1", {"role": "user"}, headers=auth_headers(admin_token))
check("不能改自己角色", s == 400, r.get("message", ""))

# 4.6 系统日志
s, r = req("GET", "/api/admin/logs?page=1", headers=auth_headers(admin_token))
check("系统日志", s == 200, "")

# 4.7 日志筛选
s, r = req("GET", "/api/admin/logs?action=LOGIN", headers=auth_headers(admin_token))
check("日志按类型筛选", s == 200, "")

# 4.8 普通用户无权
s, r = req("GET", "/api/admin/statistics", headers=auth_headers(user_token))
check("普通用户无权访问后台", s == 403, r.get("message", ""))

# 4.9 Agent 指标
s, r = req("GET", "/api/admin/metrics", headers=auth_headers(admin_token))
check("Agent指标", s == 200, "")


# ============================================================
print("\n" + "=" * 60)
print("  五、企微回调与集成")
print("=" * 60)

# 5.1 企微连接状态
s, r = req("GET", "/api/wecom/status", headers=auth_headers(admin_token))
check("企微连接状态", s == 200 and "corp_id" in r.get("data", {}), "")

# 5.2 Token 测试
s, r = req("POST", "/api/wecom/test-token", headers=auth_headers(admin_token))
check("Token获取测试", s == 200 and r.get("data", {}).get("ok"), r.get("message", ""))

# 5.3 审批记录
s, r = req("GET", "/api/wecom/approval-records?page=1", headers=auth_headers(admin_token))
check("审批记录查询", s == 200, "")

# 5.4 日程记录
s, r = req("GET", "/api/wecom/schedule-records?page=1", headers=auth_headers(admin_token))
check("日程记录查询", s == 200, "")

# 5.5 客户运营记录
s, r = req("GET", "/api/wecom/customer-records?page=1", headers=auth_headers(admin_token))
check("客户运营记录", s == 200, "")

# 5.6 非管理员无权
s, r = req("GET", "/api/wecom/status", headers=auth_headers(user_token))
check("普通用户无权查看企微状态", s == 403, "")

# 5.7 管理端代提交审批
s, r = req("POST", "/api/wecom/approval-submit",
           {"user_id": "XuQi", "template_name": "请假",
            "fields": {"leave_type": "年假", "start_date": "2026-06-21", "end_date": "2026-06-23", "days": 3, "reason": "测试"}},
           headers=auth_headers(admin_token))
check("管理端代提交审批", s == 200, r.get("message", ""))


# ============================================================
print("\n" + "=" * 60)
print("  六、15 个 Agent Tool 端点")
print("=" * 60)

# --- 审批引擎 (6) ---
s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "我要请假3天回家休息", "name": "徐琦"}, TOOL_HEADERS)
check("审批-意图解析", s == 200 and r.get("data", {}).get("approval_type") == "请假", "")

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "申请加班2天", "name": "徐琦"}, TOOL_HEADERS)
check("审批-加班意图", s == 200 and r.get("data", {}).get("approval_type") == "加班", "")

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "报销差旅费500元"}, TOOL_HEADERS)
check("审批-报销意图", s == 200 and r.get("data", {}).get("approval_type") == "报销", "")

s, r = req("POST", "/api/tools/approval/schema",
           {"template_name": "请假"}, TOOL_HEADERS)
check("审批-获取Schema", s == 200 and len(r.get("data", {}).get("controls", [])) == 5,
      f"controls={len(r.get('data', {}).get('controls', []))}")

s, r = req("POST", "/api/tools/approval/build-card",
           {"approval_type": "请假", "fields": {"leave_type": "年假", "start_date": "2026-06-20",
            "end_date": "2026-06-22", "days": 3, "reason": "回家"}, "task_id": "test_001"}, TOOL_HEADERS)
check("审批-构建卡片", s == 200 and r.get("data", {}).get("card_type") == "text_notice", "")

s, r = req("POST", "/api/tools/approval/submit",
           {"user_id": "XuQi", "template_name": "请假",
            "fields": {"leave_type": "年假", "start_date": "2026-06-20", "end_date": "2026-06-22", "days": 3, "reason": "回家"}}, TOOL_HEADERS)
check("审批-提交", s == 200 and "sp_no" in r.get("data", {}), r.get("message", ""))
sp_no = r.get("data", {}).get("sp_no", "")

s, r = req("POST", "/api/tools/approval/submit",
           {"user_id": "XuQi", "template_name": "请假", "fields": {}}, TOOL_HEADERS)
check("审批-空字段拒绝", s == 400, r.get("message", ""))

s, r = req("POST", "/api/tools/approval/query",
           {"sp_no": sp_no}, TOOL_HEADERS)
check("审批-状态查询", s == 200, "")

s, r = req("GET", "/api/tools/approval/records?page=1", headers=TOOL_HEADERS)
check("审批-记录列表", s == 200, "")

# --- 通讯录 (3) ---
s, r = req("POST", "/api/tools/contact/search",
           {"query": "徐琦"}, TOOL_HEADERS)
check("通讯录-搜索成员", s == 200 and r.get("data", {}).get("total", 0) > 0,
      f"total={r.get('data', {}).get('total', 0)}")

s, r = req("POST", "/api/tools/contact/department",
           {"dept_id": 1, "recursive": True}, TOOL_HEADERS)
check("通讯录-部门成员", s == 200 and r.get("data", {}).get("total", 0) > 0, "")

s, r = req("POST", "/api/tools/contact/report-chain",
           {"name": "徐琦"}, TOOL_HEADERS)
check("通讯录-汇报链(中文名)", s == 200 and "chain" in r.get("data", {}), "")

s, r = req("POST", "/api/tools/contact/report-chain",
           {"user_id": "XuQi"}, TOOL_HEADERS)
check("通讯录-汇报链(userid)", s == 200, "")

s, r = req("POST", "/api/tools/contact/report-chain",
           {"name": "不存在的人xyz"}, TOOL_HEADERS)
check("通讯录-查无此人", s == 404, r.get("message", ""))

# --- 日程 (3) ---
s, r = req("POST", "/api/tools/calendar/check-busy",
           {"user_ids": ["XuQi"], "start_time": "2026-06-17T09:00:00", "end_time": "2026-06-17T18:00:00"}, TOOL_HEADERS)
check("日程-查忙闲", s == 200 and "free_slots" in r.get("data", {}), "")

s, r = req("POST", "/api/tools/calendar/check-busy",
           {"user_ids": ["XuQi", "XiYang"], "start_time": "2026-06-17T09:00:00", "end_time": "2026-06-17T18:00:00"}, TOOL_HEADERS)
check("日程-多人忙闲", s == 200, "")

s, r = req("POST", "/api/tools/calendar/book",
           {"organizer": "XuQi", "attendees": ["XiYang"], "subject": "测试项目周会",
            "start_time": "2026-06-17T14:00:00", "end_time": "2026-06-17T15:00:00", "room": "A301"}, TOOL_HEADERS)
check("日程-预约会议", s == 200 and "schedule_id" in r.get("data", {}), r.get("message", ""))

s, r = req("POST", "/api/tools/calendar/book",
           {"organizer": "", "subject": ""}, TOOL_HEADERS)
check("日程-缺参数拒绝", s == 400, r.get("message", ""))

s, r = req("POST", "/api/tools/calendar/get",
           {"user_id": "XuQi"}, TOOL_HEADERS)
check("日程-获取日历", s == 200, "")

# --- 客户运营 (3) ---
s, r = req("POST", "/api/tools/customer/tag",
           {"user_id": "XuQi", "external_userid": "wmtest001", "tag_names": ["VIP客户", "重点跟进"]}, TOOL_HEADERS)
check("客户-打标签", s == 200 and r.get("data", {}).get("tags_applied"), "")

s, r = req("POST", "/api/tools/customer/broadcast",
           {"user_id": "XuQi", "external_userid": "wmtest001", "text": "您好，关于合作事宜..."}, TOOL_HEADERS)
check("客户-群发任务", s == 200, r.get("message", ""))

s, r = req("POST", "/api/tools/customer/check-follow",
           {"external_userid": "wmtest001"}, TOOL_HEADERS)
check("客户-查跟进", s == 200 and r.get("data", {}).get("name"), "")

# --- 知识库 (1) ---
s, r = req("POST", "/api/tools/knowledge/search",
           {"query": "年假政策"}, TOOL_HEADERS)
check("知识库-检索", s == 200 and "answer" in r.get("data", {}),
      f"sources={len(r.get('data', {}).get('sources', []))}")

s, r = req("POST", "/api/tools/knowledge/search",
           {"query": ""}, TOOL_HEADERS)
check("知识库-空查询拒绝", s == 400, "")


# ============================================================
print("\n" + "=" * 60)
print("  七、安全与认证")
print("=" * 60)

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "test"}, {"Content-Type": "application/json"})
check("Tool API Key缺失", s == 401, "")

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "test"}, {"Content-Type": "application/json", "X-Tool-API-Key": "wrong_key"})
check("Tool API Key错误", s == 401, "")

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "test"}, {"Content-Type": "application/json", "X-Nexus-Token": "test_api_key"})
check("百炼 Nexus-Token 兼容", s == 200, "")

s, r = req("POST", "/api/tools/approval/parse-intent",
           {"user_message": "test"}, {"Content-Type": "application/json", "Authorization": "Bearer test_api_key"})
check("百炼 Bearer Token 兼容", s == 200, "")

# 方法不允许
conn = http.client.HTTPConnection("localhost", 5000, timeout=10)
conn.request("GET", "/api/tools/approval/parse-intent")
resp = conn.getresponse()
check("GET访问POST端点", resp.status == 405, f"status={resp.status}")
conn.close()

# 404
s, r = req("GET", "/api/nonexistent_route")
check("404路由", s == 404, "")


# ============================================================
print("\n" + "=" * 60)
print("  八、E2E 端到端业务流程")
print("=" * 60)

# E2E-1: 对话式审批全流程
r1 = req("POST", "/api/tools/approval/parse-intent",
         {"user_message": "我要请年假5天去旅游", "name": "徐琦"}, TOOL_HEADERS)
r2 = req("POST", "/api/tools/approval/schema", {"template_name": "请假"}, TOOL_HEADERS)
r3 = req("POST", "/api/tools/approval/build-card",
         {"approval_type": "请假", "fields": {"leave_type": "年假", "start_date": "2026-07-01",
          "end_date": "2026-07-05", "days": 5, "reason": "旅游"}}, TOOL_HEADERS)
r4 = req("POST", "/api/tools/approval/submit",
         {"user_id": "XuQi", "template_name": "请假",
          "fields": {"leave_type": "年假", "start_date": "2026-07-01", "end_date": "2026-07-05", "days": 5, "reason": "旅游"}}, TOOL_HEADERS)
sp = r4[1].get("data", {}).get("sp_no", "")
r5 = req("POST", "/api/tools/approval/query", {"sp_no": sp}, TOOL_HEADERS)
e2e1_ok = all(r[0] == 200 for r in [r1, r2, r3, r4, r5])
check("E2E-对话式审批全流程", e2e1_ok,
      f"parse={r1[0]} schema={r2[0]} card={r3[0]} submit={r4[0]} query={r5[0]}")

# E2E-2: 智能组织大脑 + 日程
c1 = req("POST", "/api/tools/contact/search", {"query": "徐琦"}, TOOL_HEADERS)
c2 = req("POST", "/api/tools/contact/report-chain", {"user_id": "XuQi"}, TOOL_HEADERS)
c3 = req("POST", "/api/tools/calendar/check-busy",
         {"user_ids": ["XuQi"], "start_time": "2026-07-01T09:00:00", "end_time": "2026-07-01T18:00:00"}, TOOL_HEADERS)
c4 = req("POST", "/api/tools/calendar/book",
         {"organizer": "XuQi", "attendees": ["XiYang"], "subject": "季度复盘会",
          "start_time": "2026-07-01T14:00:00", "end_time": "2026-07-01T15:30:00", "room": "B201"}, TOOL_HEADERS)
e2e2_ok = all(r[0] == 200 for r in [c1, c2, c3, c4])
check("E2E-组织大脑+日程", e2e2_ok,
      f"search={c1[0]} chain={c2[0]} busy={c3[0]} book={c4[0]}")

# E2E-3: 客户运营
t1 = req("POST", "/api/tools/customer/tag",
         {"user_id": "XuQi", "external_userid": "wmtest001", "tag_names": ["季度重点"]}, TOOL_HEADERS)
t2 = req("POST", "/api/tools/customer/broadcast",
         {"user_id": "XuQi", "external_userid": "wmtest001", "text": "尊敬的用户，新产品已上线，欢迎了解"}, TOOL_HEADERS)
t3 = req("POST", "/api/tools/customer/check-follow", {"external_userid": "wmtest001"}, TOOL_HEADERS)
e2e3_ok = all(r[0] == 200 for r in [t1, t2, t3])
check("E2E-客户运营", e2e3_ok,
      f"tag={t1[0]} broadcast={t2[0]} follow={t3[0]}")

# E2E-4: 知识库全流程（上传→提问→验证来源→删除）
# 上传一个独特内容的文档
unique_content = f"E2E测试文档内容：公司年会将于7月15日在杭州国际会议中心举行。本次测试ID={int(time.time())}。"
unique_file = os.path.join(os.path.dirname(__file__), "_e2e_test_upload.txt")
with open(unique_file, "w", encoding="utf-8") as f:
    f.write(unique_content)

s, up_r = upload_document(admin_token, unique_file, "E2E测试-年会通知", "行政管理")
e2e4_up_ok = s == 201
e2e4_doc_id = up_r.get("data", {}).get("id", 0)

# 等一下让 RAG 索引生效
import time as _t
_t.sleep(1)

# 提问
s, ask_r = req("POST", "/api/qa/ask", {"question": "公司年会在哪里举行？"}, headers=auth_headers(user_token))
e2e4_ask_ok = s == 200
e2e4_sources = len(ask_r.get("data", {}).get("sources", []))

# 删除
s, del_r = req("DELETE", f"/api/documents/{e2e4_doc_id}", headers=auth_headers(admin_token))
e2e4_del_ok = s == 200

check("E2E-知识库全流程(上传→提问→删除)",
      e2e4_up_ok and e2e4_ask_ok and e2e4_del_ok,
      f"upload={e2e4_up_ok} ask_ok={e2e4_ask_ok} sources={e2e4_sources} delete={e2e4_del_ok}")


# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"  测试完成: {passed}/{total} 通过, {failed} 失败")
if failed:
    print("  失败详情:")
    for e in errors:
        print(f"    - {e}")
print("=" * 60)

# 清理临时文件
for f in [test_file, unsupported_file, unique_file]:
    try:
        os.remove(f)
    except:
        pass

sys.exit(0 if failed == 0 else 1)
