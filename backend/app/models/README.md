# models 目录说明

## 核心作用
定义 SQLAlchemy ORM 模型，映射数据库表结构与字段约束。

## 包含模块
- `base.py`：统一基类（主键、创建时间、更新时间）。
- `users.py`：用户与 token 表。
- `history.py`：面试记录与评估报告表。
- `resume.py`：简历结构化数据表。
- `rag_schema.py`：岗位、题库、知识库、文档分块等 RAG 相关表。

## 调用关系
`crud` 与 `services` 基于模型执行查询与持久化，`main.py` 启动时基于模型自动建表。

