"""
简历存储模型
用于保存用户上传和分析后的简历数据
"""
from typing import Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Resume(Base):
    """
    简历信息表
    存储用户上传的简历及其分析结果
    """
    __tablename__ = "resumes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )
    file_name: Mapped[str] = mapped_column(String(255), comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(500), comment="文件存储路径")

    # 简历结构化数据（JSON 格式）
    basic_info: Mapped[Optional[dict]] = mapped_column(JSON, comment="基本信息")
    education: Mapped[Optional[list]] = mapped_column(JSON, comment="教育经历", default=lambda: [])
    experience: Mapped[Optional[list]] = mapped_column(JSON, comment="工作经历", default=lambda: [])
    projects: Mapped[Optional[list]] = mapped_column(JSON, comment="项目经验", default=lambda: [])
    skills: Mapped[Optional[list]] = mapped_column(JSON, comment="技能清单", default=lambda: [])

    # 优化后的版本
    optimized_basic_info: Mapped[Optional[dict]] = mapped_column(JSON, comment="优化后的基本信息", nullable=True)
    optimized_education: Mapped[Optional[list]] = mapped_column(JSON, comment="优化后的教育经历", nullable=True)
    optimized_experience: Mapped[Optional[list]] = mapped_column(JSON, comment="优化后的工作经历", nullable=True)
    optimized_projects: Mapped[Optional[list]] = mapped_column(JSON, comment="优化后的项目经验", nullable=True)
    optimized_skills: Mapped[Optional[list]] = mapped_column(JSON, comment="优化后的技能清单", nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="uploaded", comment="状态")

    __table_args__ = (
        # get_user_resumes 按 user_id 查询
        Index("idx_resume_user_id", "user_id"),
    )
