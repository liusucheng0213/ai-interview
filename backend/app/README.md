# backend/app 目录说明

## 核心作用
后端业务主代码目录，提供 API、业务服务、数据模型、数据库访问与通用工具。

## 包含模块
- `config/`：配置与初始化。
- `routers/`：HTTP 接口层。
- `services/`：业务与模型调用层。
- `crud/`：数据访问层。
- `models/`：ORM 模型。
- `schemas/`：Pydantic 请求/响应模型。
- `utils/`：通用工具与辅助函数。

## 核心文件功能
- `main.py`：应用启动入口、生命周期初始化、路由注册。

## 调用关系
`routers -> services -> crud/models`，`schemas` 负责接口数据约束，`config` 提供运行参数与资源初始化。

