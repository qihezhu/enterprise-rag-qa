# 百炼平台 Tool 注册规格

**Base URL**: `https://latin-caution-proprietary-hopefully.trycloudflare.com`
**Auth Header**: `X-Tool-API-Key: test_api_key`
**Method**: 全部 `POST`

---

## 一、审批模块（5 个）

### 1. 审批意图解析
- **URL**: `/api/tools/approval/parse-intent`
- **描述**: 从自然语言中识别审批类型、提取关键字段（天数、日期等）
- **输入**:
```json
{"user_message": "我要请假3天从下周一开始", "user_id": "zhangsan"}
```
- **输出**: `{"approval_type": "请假", "fields": {...}, "suggested_template": "请假", "confidence": 0.85}`

### 2. 获取审批模板Schema
- **URL**: `/api/tools/approval/schema`
- **描述**: 获取审批模板的字段定义（动态控件列表）
- **输入**:
```json
{"template_name": "请假"}
```
- **输出**: `{"template_name": "请假", "controls": [{"name": "请假类型", "type": "selector", "required": true, "options": [...]}]}`

### 3. 构建确认卡片
- **URL**: `/api/tools/approval/build-card`
- **描述**: 生成企微模板卡片JSON，用于用户确认审批信息
- **输入**:
```json
{"approval_type": "请假", "fields": {"请假类型": "年假", "开始日期": "6月17日"}}
```
- **输出**: `{"card_type": "text_notice", "main_title": {...}, "button_selection": {...}}`

### 4. 提交审批
- **URL**: `/api/tools/approval/submit`
- **描述**: 提交审批申请到企微OA系统。`name` 支持传入中文姓名，后端自动解析 userid。`fields` 的 key 支持英文ID（如 `leave_type`）和中文名（如 `请假类型`）两种格式。
- **输入（请假）**:
```json
{"name": "张三", "template_name": "请假", "fields": {"leave_type": "年假", "start_date": "2026-06-17", "end_date": "2026-06-18", "days": 2, "reason": "个人原因"}}
```
- **输入（加班）**:
```json
{"name": "张三", "template_name": "加班", "fields": {"overtime_date": "2026-06-17", "overtime_hours": 3, "overtime_reason": "赶项目进度"}}
```
- **输入（报销）**:
```json
{"name": "张三", "template_name": "报销", "fields": {"expense_type": "差旅费", "expense_amount": 500, "expense_reason": "出差交通费"}}
```
- **输出**: `{"sp_no": "DEMO-20260617170000-zhangsan", "status": "submitted"}`

### 5. 查询审批状态
- **URL**: `/api/tools/approval/query`
- **描述**: 根据审批单号查询审批进度
- **输入**:
```json
{"sp_no": "20250617001"}
```
- **输出**: `{"sp_no": "...", "status": "审批中", "applicant": "zhangsan", "detail": {...}}`

---

## 二、通讯录模块（3 个）

### 6. 搜索成员
- **URL**: `/api/tools/contact/search`
- **描述**: 按姓名或手机号搜索企业成员
- **输入**:
```json
{"query": "张三 或 13812345678"}
```
- **输出**: `{"results": [{"userid": "...", "name": "张三", "department": "...", "mobile": "138****1234"}], "total": 1}`

### 7. 查询部门成员
- **URL**: `/api/tools/contact/department`
- **描述**: 获取指定部门成员列表，支持递归子部门
- **输入**:
```json
{"dept_id": 1, "recursive": true}
```
- **输出**: `{"dept_id": 1, "members": [...], "total": N}`

### 8. 查询汇报链
- **URL**: `/api/tools/contact/report-chain`
- **描述**: 查询某人的汇报链，向上遍历部门层级
- **输入**:
```json
{"user_id": "zhangsan"}
```
- **输出**: `{"user_id": "zhangsan", "chain": [{"name": "张三", "position": "经理"}, ...]}`

---

## 三、日程模块（3 个）

### 9. 查询忙闲
- **URL**: `/api/tools/calendar/check-busy`
- **描述**: 查询指定用户在某时间段的忙闲状态
- **输入**:
```json
{"user_ids": ["zhangsan", "lisi"], "start_time": "2026-06-17T09:00:00", "end_time": "2026-06-17T18:00:00"}
```
- **输出**: `{"busy_slots": [...], "free_slots": [...]}`

### 10. 预约会议
- **URL**: `/api/tools/calendar/book`
- **描述**: 创建日程/预约会议
- **输入**:
```json
{"organizer": "zhangsan", "attendees": ["lisi"], "subject": "周会", "start_time": "2026-06-17T15:00", "end_time": "2026-06-17T16:00", "room": "A301"}
```
- **输出**: `{"schedule_id": "...", "status": "created"}`

### 11. 获取日历
- **URL**: `/api/tools/calendar/get`
- **描述**: 获取用户的日历列表
- **输入**:
```json
{}
```
- **输出**: `{"calendar_list": [...]}`

---

## 四、客户运营模块（4 个）

### 12. 搜索外部联系人
- **URL**: `/api/tools/customer/search`
- **描述**: 按姓名搜索外部联系人，返回 external_userid 和详情。打标签前必须先调此工具获取 external_userid。
- **输入**:
```json
{"name": "文玺", "user_id": "XuQi"}
```
- **输出**: `{"results": [{"external_userid": "woRG6jDgAA...", "name": "文玺", "position": "经理", "corp_name": "演示公司"}], "total": 1}`

### 13. 打标签
- **URL**: `/api/tools/customer/tag`
- **描述**: 为企业微信外部联系人打标签
- **输入**:
```json
{"user_id": "zhangsan", "external_userid": "wmxxxxx", "tag_names": ["VIP客户", "重点跟进"]}
```
- **输出**: `{"tags_applied": ["VIP客户"], "record_id": N}`

### 14. 创建群发任务
- **URL**: `/api/tools/customer/broadcast`
- **描述**: 创建客户群发消息任务
- **输入**:
```json
{"user_id": "zhangsan", "external_userid": "wmxxxxx", "text": "您好，关于..."}
```
- **输出**: `{"msg_id": "...", "record_id": N}`

### 15. 查询客户跟进
- **URL**: `/api/tools/customer/check-follow`
- **描述**: 查询客户联系详情和跟进状态
- **输入**:
```json
{"external_userid": "wmxxxxx"}
```
- **输出**: `{"name": "...", "tags": [...], "follow_users": [...], "last_contact": "..."}`

---

## 五、知识库模块（1 个）

### 16. 知识库检索
- **URL**: `/api/tools/knowledge/search`
- **描述**: 基于RAG的知识库检索问答，从企业文档中查找答案
- **输入**:
```json
{"query": "公司年假政策是什么？", "topic": "人力资源"}
```
- **输出**: `{"answer": "...", "sources": [{"file_name": "...", "content_preview": "...", "relevance_score": 0.95}]}`
