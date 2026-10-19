# Backend 目录说明

## 核心作用
后端服务端实现，负责接口提供、业务编排、数据持久化、RAG 检索、LLM 调用和报告生成。

## 包含模块
- `app/`：业务主代码。
- `tests/`：后端测试用例。
- `requirements.txt`：Python 依赖。
- `.env.example`：环境变量模板。复制为 `.env` 后填写，不要提交 `.env`。

## 核心文件功能
- `app/main.py`：应用入口、生命周期初始化（含自动建表）。
- `requirements.txt`：后端安装依赖集合。

## 调用关系
前端请求进入 `app/routers/*`，由 `services/*` 执行业务逻辑，`crud/*` 负责数据库读写，`models/*` 映射表结构。

