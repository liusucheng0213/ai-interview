"""
知识库结构化 schema：job / question / knowledge_file；父子块表与 Chroma 子块集合一一对应（chroma_id）。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class KnowledgeFile(Base):
    """知识库文件元信息"""

    __tablename__ = "knowledge_file"

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="上传用户")
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="服务器相对路径")
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="扩展名类别")
    category: Mapped[str] = mapped_column(String(64), default="general", comment="业务分类")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        comment="pending|parsing|structuring|chunking|vectorizing|done|error",
    )
    parse_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    child_chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    visibility: Mapped[str] = mapped_column(String(32), default="user_local", comment="user_local|enterprise_global")
    org_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_kf_user", "user_id"),
        Index("idx_kf_status", "parse_status"),
    )


class Job(Base):
    """岗位表"""

    __tablename__ = "job"

    job_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="岗位名称")
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="技术栈 JSON")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="岗位描述")
    source_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_file.id", ondelete="SET NULL"), nullable=True, comment="来源文件"
    )
    main_chunk_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="关联 document_chunks.chunk_id 的岗位主块"
    )

    __table_args__ = (Index("idx_job_name", "job_name"),)


class Question(Base):
    """题库表"""

    __tablename__ = "question"

    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="题干")
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="参考答案")
    difficulty: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="难度")
    exam_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="考点")
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="分类")
    source_file_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("knowledge_file.id", ondelete="SET NULL"), nullable=True
    )
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Excel 行号")
    generate_time: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="AI 生成时间")

    __table_args__ = (
        Index("idx_q_job", "job_id"),
        Index("idx_q_diff", "difficulty"),
        Index("idx_q_cat", "category"),
    )


class KbParentChunk(Base):
    """父块"""

    __tablename__ = "kb_parent_chunk"

    knowledge_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_file.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str] = mapped_column(String(32), default="doc", comment="excel_row|doc_heading|txt_block")
    source_row: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preview: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    __table_args__ = (Index("idx_kb_parent_file", "knowledge_file_id"),)


class KbChildChunk(Base):
    """子块（向量单元）"""

    __tablename__ = "kb_child_chunk"

    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("kb_parent_chunk.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_file_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("knowledge_file.id", ondelete="CASCADE"), nullable=False
    )
    seq: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chroma_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)
    char_len: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_kb_child_file", "knowledge_file_id"),
        Index("idx_kb_child_parent", "parent_id"),
    )


class Document(Base):
    """Plan1 文档主表（RAG 检索底座）。"""

    __tablename__ = "documents"

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    upload_time: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")

    __table_args__ = (
        Index("idx_documents_filename", "filename"),
        Index("idx_documents_file_type", "file_type"),
    )


class DocumentChunk(Base):
    """Plan1 分块表（父子索引 + 业务分类 + 哈希）。"""

    __tablename__ = "document_chunks"

    doc_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_level: Mapped[str] = mapped_column(String(16), nullable=False, comment="parent|child")
    parent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    chunk_type: Mapped[str] = mapped_column(String(32), default="other")
    job_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("job.id", ondelete="SET NULL"), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_document_chunks_doc", "doc_id"),
        Index("idx_document_chunks_parent", "parent_id"),
        Index("idx_document_chunks_type", "chunk_type"),
        Index("idx_document_chunks_hash", "content_hash"),
    )
