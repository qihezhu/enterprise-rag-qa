---
name: pre-deploy-check
description: 部署前检查清单，覆盖环境验证、隧道配置、企微回调、百炼平台同步等关键步骤
type: skill
---

# 部署前检查 Skill

## 适用场景
每次部署（或重启服务）前执行，确保所有依赖和配置正确。

## 检查清单

### 一、环境服务
- [ ] MySQL 8.0 运行中，数据库 `db_enterprise_ge` 可连接
- [ ] Redis 运行中（如不可用，确认 token 缓存已降级为内存模式）
- [ ] Ollama 运行中，`qwen3:8b` 和 `qwen3-embedding:4b` 已拉取
- [ ] ChromaDB 持久化目录 `server/chroma_db/` 有数据

### 二、企微配置
- [ ] 回调 URL 已更新为当前 cloudflared 隧道地址
- [ ] 回调验证状态为"已保存通过"
- [ ] 18/18 API 权限全部开通
- [ ] CorpID / AgentID / Secret 与 `config.py` 一致

### 三、百炼平台
- [ ] Tool Base URL 已更新为当前 cloudflared 隧道地址
- [ ] Tool API Key 与 `config.py` 中的 `QWEN_TOOL_API_KEY` 一致
- [ ] 15 个 Tool 端点均可通过公网访问

### 四、启动流程
```bash
# 1. 启动 Flask
cd enterprise-rag-qa
python run.py

# 2. 启动公网隧道
./cloudflared.exe tunnel --url http://localhost:5000

# 3. 获取新隧道 URL 后更新：
#    - 企微后台 → 回调 URL
#    - 百炼平台 → Tool Base URL
```

### 五、验证
- [ ] `GET /api/wecom/status` 返回正常
- [ ] `POST /api/tools/approval/parse-intent` 通过公网可访问
- [ ] `POST /api/qa/ask` RAG 问答正常返回
- [ ] 企微应用发送消息能收到回调

### 已知陷阱
- **隧道 URL 变化**：每次重启 cloudflared，URL 会变，必须手动更新两处
- **Redis 兼容性**：旧版 Redis 不支持 HELLO 命令，token 缓存会自动降级
- **Ollama 内存**：`qwen3:8b` 约需 8GB 显存/内存，确保资源充足
