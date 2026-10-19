# config 目录说明

## 核心作用
管理后端运行配置、模型配置、缓存配置、数据库连接和日志配置。

## 包含模块
- `db_conf.py`：数据库连接与会话工厂。
- `llm_conf.py`：LLM 模型参数与调用封装。
- `rag_conf.py`：RAG embedding 与向量配置。
- `cache_conf.py`：Redis 初始化与缓存能力。
- `logger_conf.py`：日志格式与级别初始化。

## 调用关系
`main.py` 生命周期启动时调用配置初始化，`routers/services/crud` 按需读取配置项。

