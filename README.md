# AI 智能面试模拟与成长指导系统

面向求职者的模拟面试与能力提升系统，同时提供企业端面试记录查看能力。项目灵感来自第十七届大学生创新创业大赛企业赛题【A05】「AI 模拟面试与能力提升软件」（出题企业：锐捷网络），获第十七届中国大学生服务外包创新创业大赛东部区域赛企业命题类三等奖。

## 功能一览

| 模块 | 已实现能力 |
| --- | --- |
| 模拟面试 | 按岗位进行文字、语音或视频面试，生成评估报告 |
| 简历助手 | 简历解析、优化与导出 |
| 知识库 | 文件上传、检索及基于检索结果的提问 |
| 成长指导 | 查看历史成绩、能力变化与学习建议 |
| 企业端 | 查看面试记录与相关结果 |
| 数字人 | 可选的讯飞虚拟人面试官 |

## 技术栈

- **前端**：Vue 3、Vite、Element Plus、Vue Router。
- **后端**：FastAPI、SQLAlchemy、MySQL；Redis 为可选缓存。
- **模型与检索**：DeepSeek 负责文本与视觉理解；本地 `bge-small-zh-v1.5` 负责知识库向量；本地 Whisper 负责语音转写。
- **可选能力**：讯飞虚拟人及对应前端 SDK。

> DeepSeek 不提供本项目所需的 Embedding 接口，因此知识库使用 512 维本地向量模型。若旧向量库使用其他维度，需要重新上传知识库。

## 环境要求

- Python 3.10 或 3.11（推荐）
- Node.js 18+ 与 npm
- MySQL 8+
- FFmpeg（Whisper 处理音频所需）
- Redis（可选，未连接时缓存能力受限）
- 讯飞账号与对应服务授权（仅数字人功能需要）

## 快速启动

以下命令以 Windows PowerShell 为例。macOS / Linux 的虚拟环境激活命令为 `source .venv/bin/activate`。

### 1. 准备后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `backend/.env`，至少配置：

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库密码
MYSQL_DB=ai_interview
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

提前在 MySQL 中创建 `MYSQL_DB` 对应的数据库；应用启动时会自动创建数据表。其他数据库、Redis、RAG 和数字人参数见 `.env.example` 注释。

### 2. 准备本地向量模型

将 `BAAI/bge-small-zh-v1.5` 下载到：

```text
backend/app/models_rag/bge-small-zh-v1.5/
```

模型权重体积较大，不纳入 Git。未安装模型时，其他功能仍可启动，但语义检索不可用。Whisper 会在首次使用时按 `WHISPER_MODEL_NAME` 下载对应模型，因此首次语音转写可能较慢。

### 3. 启动后端

```powershell
cd backend/app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端接口文档：`http://localhost:8000/docs`。配置统一从 `backend/.env` 读取，不依赖启动时所在的目录。

### 4. 启动前端

另开终端：

```powershell
cd frontend
npm ci
npm run dev
```

访问 `http://localhost:5173`。开发服务器通过 Vite 将 `/api` 代理到 `http://localhost:8000`。

## 验证

```powershell
# 后端纯逻辑测试，不连接数据库、不调用模型
cd backend
python -m pytest tests

# 前端生产构建
cd ../frontend
npm run build
```

## 目录结构

```text
ai-interview/
├── backend/
│   ├── app/
│   │   ├── config/          # 数据库、缓存、LLM 与 RAG 配置
│   │   ├── routers/         # FastAPI 路由
│   │   ├── services/        # 业务逻辑与模型调用
│   │   ├── models_rag/      # 本地向量模型（不提交）
│   │   └── main.py          # 后端入口，启动时自动建表
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/                 # Vue 页面、组件与 API 封装
│   ├── vendor/avatar_sdk/   # 讯飞虚拟人前端 SDK
│   └── vite.config.js
└── README.md
```

更细的模块说明见 [`backend/README.md`](backend/README.md) 与 [`frontend/README.md`](frontend/README.md)。

## 常见问题

### 启动时提示数据库连接失败

确认 MySQL 已启动、`backend/.env` 中的账号密码正确，并且 `MYSQL_DB` 指向的数据库已经存在。自动建表不会自动创建数据库本身。

### Redis 或 RAG 初始化失败

Redis 和本地向量模型不会阻止 FastAPI 主进程启动，但对应缓存或语义检索能力不可用。请查看启动日志中的具体路径或连接错误。

### 数字人无法使用

数字人是可选模块。检查讯飞服务授权及 `.env.example` 中 `IFLYTEK_*` 配置；未配置时不影响文字面试等核心流程。

## 数据与安全

- `.env`、上传文件、向量库、模型权重和运行日志均已加入 `.gitignore`，不要提交真实密钥或用户数据。
- `MYSQL_PASSWORD` 必须显式配置，没有固定默认密码；生产环境应限制 `CORS_ORIGINS` 并使用独立、最小权限的数据库账号。
- 简历上传仅保留文件名，不接受路径，单个文件上限 20 MB；访问令牌不会写入日志。
- 本项目涉及简历、音视频与面试记录，部署前应按实际使用场景补充隐私告知、数据保留和删除策略。
