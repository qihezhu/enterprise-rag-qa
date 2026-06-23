# 企业知识库问答系统

基于 LangChain + Flask + Vue3 的 RAG（检索增强生成）企业内部知识库智能问答系统。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python Flask 3.x |
| 前端框架 | Vue 3 + Vite |
| UI组件库 | Element Plus |
| 数据库 | MySQL 8.0 |
| 向量数据库 | Chroma（本地持久化） |
| 大语言模型 | Ollama + qwen3:8b |
| 嵌入模型 | Ollama + qwen3-embedding:4b |
| RAG框架 | LangChain |
| 图表 | ECharts 5 |

## 项目结构

```
enterprise-rag-qa/
├── server/                 # 后端Flask应用
│   ├── app.py              # 应用入口
│   ├── config.py           # 配置文件
│   ├── models/             # 数据模型
│   ├── routes/             # API路由
│   ├── services/           # 业务逻辑（RAG、文档解析、向量库）
│   └── middleware/         # 认证中间件
├── client/                 # 前端Vue3应用
│   └── src/
│       ├── views/          # 页面（user/ admin/）
│       ├── components/     # 公共组件
│       ├── stores/         # Pinia状态管理
│       ├── api/            # API接口层
│       └── router/         # 路由配置
└── sql/                    # 数据库脚本
    ├── init.sql            # 建库建表
    └── seed.sql            # 测试数据
```

## 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0+
- Ollama（需提前拉取模型）

## 快速启动

### 1. 安装Ollama并拉取模型

```bash
# 安装Ollama（https://ollama.com）
ollama pull qwen3:8b
ollama pull qwen3-embedding:4b
```

### 2. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
mysql -u root -p < sql/seed.sql
```

### 3. 启动后端

```bash
cd server
pip install -r requirements.txt
python app.py
# 服务启动在 http://localhost:5000
```

### 4. 启动前端

```bash
cd client
npm install
npm run dev
# 服务启动在 http://localhost:3000
```

### 5. 访问系统

打开浏览器访问 http://localhost:3000

- 管理员账号：admin / 123456
- 管理员账号：zhangsan / 123456
- 普通用户：lisi / 123456
- 普通用户：wangwu / 123456
- 普通用户：zhaoliu / 123456

## 功能说明

### 普通用户
- 首页：统计面板
- 智能问答：基于知识库的RAG问答
- 文档管理：上传、查看、删除自己的知识文档

### 管理员
- 仪表盘：系统数据统计（用户数、文档数、提问趋势图表）
- 用户管理：查看、启用/禁用、修改角色、删除用户
- 文档管理：查看和管理所有知识文档
- 系统日志：查看操作日志

## API接口

| 路径 | 方法 | 说明 | 权限 |
|------|------|------|------|
| /api/auth/login | POST | 用户登录 | 公开 |
| /api/auth/register | POST | 用户注册 | 公开 |
| /api/auth/userinfo | GET | 当前用户信息 | 登录 |
| /api/documents | GET | 文档列表 | 登录 |
| /api/documents | POST | 上传文档 | 登录 |
| /api/documents/:id | DELETE | 删除文档 | 上传者/admin |
| /api/qa/ask | POST | 智能问答 | 登录 |
| /api/qa/history | GET | 对话历史 | 登录 |
| /api/admin/statistics | GET | 仪表盘数据 | admin |
| /api/admin/users | GET | 用户列表 | admin |
| /api/admin/logs | GET | 系统日志 | admin |
