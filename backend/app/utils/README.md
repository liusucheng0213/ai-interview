# utils 目录说明

## 核心作用
封装跨模块复用的通用能力，如鉴权、响应结构、PDF 导出、知识图谱辅助处理等。

## 包含模块
- `auth.py`：Token 解析与当前用户获取。
- `response.py`：统一响应封装。
- `pdf_export.py`：简历与评估报告 PDF 导出。
- `knowledge_map.py`：知识图谱结构构建辅助。
- `learning_resources.py`：学习资源拼装辅助。

## 调用关系
被 `routers` 与 `services` 广泛复用，降低重复实现成本。

