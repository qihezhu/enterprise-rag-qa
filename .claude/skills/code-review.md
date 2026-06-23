---
name: code-review
description: 针对本项目的代码审查清单，覆盖安全、认证、API 规范、RAG 质量等关键检查项
type: skill
---

# 代码审查 Skill

## 适用场景
对本项目任何 PR 或代码变更进行审查时使用。

## 审查清单

### 认证与授权
- [ ] 新路由是否添加了 `@login_required` 装饰器（除公开端点外）
- [ ] 管理端点是否验证了 `admin` 角色
- [ ] Tool 端点是否验证了 `X-Tool-API-Key` 请求头
- [ ] 是否兼容百炼平台的 `X-Nexus-Token` 和 `Authorization: Bearer` 两种认证方式

### 安全
- [ ] 用户输入是否经过校验（长度、类型、SQL 注入防护）
- [ ] 文件上传是否限制类型和大小（仅允许 pdf/docx/txt/md，最大 16MB）
- [ ] 敏感信息（API Key、Secret）不出现在日志或响应中
- [ ] JWT Token 是否正确处理过期和伪造情况

### API 规范
- [ ] 响应格式统一为 `{"code": 200, "message": "", "data": {}}`
- [ ] 错误码含义明确（400 参数错误、401 未认证、403 无权限、404 不存在、409 冲突）
- [ ] 分页接口支持 `page` 和 `page_size` 参数
- [ ] Tool 端点遵循 `/api/tools/<module>/<action>` 命名规范

### RAG 与 AI
- [ ] 文档上传后是否正确入库到 ChromaDB
- [ ] 检索参数 `top_k` 是否合理（当前默认 6）
- [ ] 问答结果是否包含来源引用
- [ ] Ollama 调用是否有超时处理

### 数据库
- [ ] 模型变更是否同步更新了 `sql/init.sql`
- [ ] 迁移脚本是否兼容现有数据
- [ ] 查询是否考虑了大数据量下的性能（索引、分页）

### 测试
- [ ] 新功能是否有对应的测试用例
- [ ] 测试使用 SQLite 内存数据库 + FakeRedis，不依赖外部服务
- [ ] 正常路径和异常路径都有覆盖
