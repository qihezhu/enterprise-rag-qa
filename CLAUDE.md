# enterprise-rag-qa

企业微信 AI Agent — 百炼平台 + RAG 知识库 + 五大业务模块。

## 技术栈
Flask 3.1 / SQLAlchemy / Redis / ChromaDB / Ollama (qwen3:8b + qwen3-embedding:4b) / MySQL 8.0 / Vue 3 + Element Plus

## 项目结构
```
server/
  app.py              — Flask 工厂，注册蓝图和扩展
  config.py           — 所有配置（含企微凭证、DB、Ollama）
  clients/            — 企微 API 客户端 (WeComClient) + 加解密
  routes/tools/       — 15 个 Agent Tool 端点（百炼平台调用）
  services/           — 业务逻辑层（5 个模块 + RAG + 事件路由）
  models/             — SQLAlchemy 模型
  middleware/         — JWT + Tool API Key 认证
  monitoring/         — 健康检查
client/               — Vue 3 前端（管理后台）
sql/                  — 数据库迁移脚本
```

## 15 个 Tool 端点（全部在 /api/tools/*）
审批 #1-5: approval/parse-intent, schema, build-card, submit, query
通讯录 #6-8: contact/search, department, report-chain
日程 #9-11: calendar/check-busy, book, get
客户 #12-14: customer/tag, broadcast, check-follow
知识库 #15: knowledge/search

## 服务启动

```bash
# 每次开发启动顺序：
cd enterprise-rag-qa
python run.py                                  # Flask :5000
./cloudflared.exe tunnel --url http://localhost:5000   # 公网穿透
```

## 当前状态

### 环境
| 服务 | 状态 |
|------|------|
| MySQL 8.0 | 运行中 (8 张表) |
| Redis | 运行中 |
| Ollama (qwen3:8b + qwen3-embedding:4b) | 运行中 |
| ChromaDB | 90 个向量 |
| Flask :5000 | 运行中 |

### 企微配置
| 项目 | 值 |
|------|-----|
| 应用名称 | 智慧办公一体化AI平台 |
| CorpID | wwd286a2dd91eab108 |
| AgentID | 1000002 |
| API 权限 | 18/18 全部开通 |
| 回调 URL | https://latin-caution-proprietary-hopefully.trycloudflare.com/api/wecom/callback |
| 回调状态 | 已保存通过 |

### 公网
| 项目 | 值 |
|------|-----|
| 隧道 | cloudflared (Cloudflare Tunnel) |
| URL | https://latin-caution-proprietary-hopefully.trycloudflare.com |
| Tool API Key | test_api_key |

### 代码修复记录
- 审批 submit() 添加了必填字段阻断校验
- WeComClient 补全了 list_user_simple/list_user 公共方法
- 修复日程 API 路径 (/cgi-bin/schedule/* → /cgi-bin/oa/schedule/*)
- 修复 update_button 路径和参数
- 单元测试 16/16 passed

### 待完成
- [x] 端到端对话测试（2026-06-17 通过）
- [x] 修复 ThreadPoolExecutor 中 current_app 缺失
- [x] 修复企微 API IP 白名单（errcode 60020）

### 已知问题
- 每次重启 cloudflared 快速隧道 URL 会变，需更新企微回调 URL 和百炼 Tool URL
- Redis 版本过旧不支持 HELLO 命令，token 缓存降级为内存模式

## MCP 服务
已配置标准 MCP 服务器（`.claude/settings.json`）：
- **Git MCP**：`@modelcontextprotocol/server-git` — 提供 git 操作能力
- **Filesystem MCP**：`@modelcontextprotocol/server-filesystem` — 提供文件系统操作能力

## 团队 Skill 资产
可复用 Skill 位于 `.claude/skills/`：

| Skill | 文件 | 用途 |
|-------|------|------|
| 重构修复 | `refactor-wecom-flask.md` | Flask/企微项目常见修复模式（API路径、校验、降级） |
| 代码审查 | `code-review.md` | PR 审查清单（认证、安全、API规范、RAG、测试） |
| 部署检查 | `pre-deploy-check.md` | 部署前环境验证（企微回调、百炼同步、隧道更新） |

### 百炼注册信息
| 项目 | 值 |
|------|-----|
| Base URL | https://latin-caution-proprietary-hopefully.trycloudflare.com |
| Auth Header | X-Tool-API-Key: test_api_key |
| 规格文档 | BAILIAN_TOOLS.md |

## CI/CD 流程

### 工作流触发（.github/workflows/ci.yml）
```
git push → GitHub Actions 触发
  ├── test-python    # pytest (SQLite + fakeredis)
  ├── test-frontend  # npm run build 验证
  ├── codeql         # CodeQL 安全扫描 (Python + JavaScript)
  └── docker-build   # Docker 镜像构建（仅 push main）
```

### Docker 容器化
| 文件 | 用途 |
|------|------|
| `Dockerfile.server` | Flask 后端 (python:3.10-slim) |
| `Dockerfile.client` | Vue3 前端多阶段构建 (node:18 → nginx:alpine) |
| `nginx.conf` | Nginx SPA 路由 + /api 反向代理 |
| `docker-compose.yml` | 编排 flask + nginx + mysql + redis + ollama(可选) |

### 本地一键部署
```bash
docker compose up -d          # 启动全部服务（Ollama 使用宿主机）
docker compose --profile full up -d  # 含 Ollama 容器的完整部署
docker compose ps              # 查看服务状态
docker compose logs -f flask   # 查看后端日志
```

### 测试
- 测试目录 `tests/` 下含 5 个测试文件，覆盖认证/文档/RAG/管理/企微/15 Tool/E2E/安全
- `conftest.py` 使用 SQLite 内存库 + fakeredis，无需外部服务
