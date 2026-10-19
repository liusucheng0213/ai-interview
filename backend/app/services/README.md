# services 目录说明

## 核心作用
承载业务核心逻辑与外部能力调用，包括 LLM 编排、RAG 检索链路、数字人服务、简历处理。

## 包含模块
- `LLM_services.py`：问题生成、回答评估、最终报告生成、多模态分析。
- `iflytek_virtual_human.py`：讯飞数字人服务端调用封装。
- `resume_services.py`：简历分析与优化逻辑。
- `kb/`：知识库入库、检索、计划服务与向量管理。

## 调用关系
`routers` 调用 `services`，`services` 再调用 `crud`、`models` 与第三方能力（DeepSeek、Chroma、Whisper 等）。

