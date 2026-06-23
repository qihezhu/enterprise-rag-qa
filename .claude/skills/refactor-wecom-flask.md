---
name: refactor-wecom-flask
description: Flask 企业微信集成项目的重构与修复指南，涵盖 API 路径修复、参数校验、客户端方法补全等常见模式
type: skill
---

# Flask + 企业微信 重构与修复 Skill

## 适用场景
对本项目中 Flask 路由、企微 API 调用、Tool 端点进行重构或修复时使用。

## 常见修复模式

### 1. 企微 API 路径修正
企微 API 路径经常因版本演进发生变化，修复时注意：
- 日程 API 使用 `/cgi-bin/oa/schedule/*`，非 `/cgi-bin/schedule/*`
- 通讯录 API 使用 `/cgi-bin/user/*` 和 `/cgi-bin/department/*`
- 审批 API 使用 `/cgi-bin/oa/approval/*`
- 每次修改 API 路径后，检查 `WeComClient` 中对应方法签名是否匹配

### 2. Tool 端点必填字段校验
所有 `/api/tools/*` 端点必须对必填字段做阻断校验：
```python
# 在 service 层入口处添加
if not required_field:
    return {"error": "missing required field", "code": 400}
```

### 3. WeComClient 公共方法补全
当需要新的企微 API 调用时：
- 在 `server/clients/wecom_client.py` 中添加方法
- 确保方法签名包含 `access_token` 参数
- 添加对应的错误处理和日志记录
- 优先使用 `list_user_simple` 而非 `list_user` 以减少 API 调用量

### 4. 回调 URL 更新
每次 `cloudflared` 重启后隧道 URL 会变化，需同步更新：
- 企微后台回调 URL：`https://<new-tunnel>/api/wecom/callback`
- 百炼平台 Tool URL：`https://<new-tunnel>/api/tools/*`
- 检查 `config.py` 中的相关配置是否需要调整

### 5. 降级策略
当外部依赖不可用时，采用降级而非崩溃：
- Redis 不可用时，token 缓存降级为内存模式
- Ollama 不可用时，返回友好错误提示而非 500
- 企微 API 超时时，设置合理的超时时间（建议 30s）

## 修复后检查清单
- [ ] 对应单元测试已更新
- [ ] `pytest` 全量通过
- [ ] 受影响的 Tool 端点手动验证
- [ ] 企微回调功能正常
