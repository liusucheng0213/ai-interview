# AI智能面试模拟与成长指导系统

## 快速启动步骤
1. 安装后端依赖并准备配置：
   - `cd backend`
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`（Windows）
   - `pip install -r requirements.txt`
   - 复制 `backend/.env.example` 为 `backend/.env` 并填写配置
2. 启动后端服务：
   - `cd backend/app`
   - `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
3. 启动前端服务：
   - `cd frontend`
   - `npm install`
   - `npm run dev`

## 核心目录结构
```text
CURSOR_WORKSPACE/
├── backend/
│   ├── app/                  # FastAPI 后端代码
│   ├── requirements.txt      # Python 依赖
│   └── .env.example          # 环境变量模板
├── frontend/
│   ├── src/                  # Vue 前端源码
│   └── package.json          # Node 依赖与脚本
├── avatar_digital_human_studio/  # 讯飞数字人 SDK 示例与资源
└── PROJECT_DOCUMENT.md       # 项目完整详细文档
```

## 依赖安装命令
```bash
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```
