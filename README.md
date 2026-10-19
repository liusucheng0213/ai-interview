# AI 智能面试模拟与成长指导系统

## 项目来源与获奖

本项目的灵感来自第十七届大学生创新创业大赛企业赛题【A05】「AI模拟面试与能力提升软件」，出题企业为锐捷网络。

项目获得第十七届中国大学生服务外包创新创业大赛东部区域赛企业命题类三等奖。

## 这个系统做什么

面向求职者的模拟面试与能力提升工具，也包含企业端查看面试记录。主要能力：

- 按岗位进行文字、语音、视频模拟面试，并生成评估报告
- 简历解析、优化与导出
- 知识库上传、检索，以及基于检索结果的提问
- 历史成绩与成长建议
- 可选的讯飞虚拟人面试官

大模型使用 DeepSeek（`deepseek-flash`）。知识库向量使用本地 `bge-small-zh`，因为 DeepSeek 不提供 Embedding 接口。语音转写使用本地 Whisper。

## 快速启动

1. 安装后端依赖并准备配置：
   - `cd backend`
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate`（Windows）
   - `pip install -r requirements.txt`
   - 复制 `backend/.env.example` 为 `backend/.env`
   - 至少填写 `DEEPSEEK_API_KEY`，以及 MySQL 连接信息
2. 启动后端服务：
   - `cd backend/app`
   - `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
3. 启动前端服务：
   - `cd frontend`
   - `npm install`
   - `npm run dev`

前端开发地址默认是 `http://localhost:5173`，接口通过 Vite 代理到 `http://localhost:8000`。

本地向量模型放在 `backend/app/models_rag/bge-small-zh-v1.5`。该目录体积较大，不纳入 Git。若以前用过其他维度的向量库，需要重新上传知识库。

## 目录结构

```text
ai-interview/
├── backend/
│   ├── app/                  # FastAPI 后端
│   ├── tests/                # 后端测试
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/                  # Vue 前端
│   ├── vendor/avatar_sdk/    # 讯飞虚拟人前端 SDK
│   ├── package.json
│   └── vite.config.js
├── .gitignore
└── README.md
```

## 依赖安装

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
