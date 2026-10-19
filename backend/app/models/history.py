from typing import Optional

from sqlalchemy import Integer, String, Text, ForeignKey, Float, Index
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.users import User


# ==================== 面试记录表 ====================
class InterviewRecordHistory(Base):
    """
    面试过程记录表
    记录每次面试的完整信息，包括用户、岗位、时间等
    """
    __tablename__ = "interview_records_history"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.id),
        comment="用户标识"
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job.id"),
        comment="岗位ID（强约束主键关联）",
    )
    position_name: Mapped[str] = mapped_column(
        String(50),
        comment="岗位名称"
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        comment="难度等级"
    )
    interview_round: Mapped[int] = mapped_column(
        Integer,
        comment="面试轮次"
    )
    interview_status: Mapped[str] = mapped_column(
        String(50),
        comment="面试状态"
    )
    chat_context: Mapped[str] = mapped_column(
        Text,
        comment="面试过程内容"
    )
    mode: Mapped[str] = mapped_column(
        String(50),
        comment="面试形式"
    )

    __table_args__ = (
        # search_now_history / get_user_history 的核心查询条件
        Index("idx_irh_user_status", "user_id", "interview_status"),
        Index("idx_irh_user_id", "user_id"),
        Index("idx_irh_user_job", "user_id", "job_id"),
    )


# ==================== 评估报告表 ====================
class EvaluationReportHistory(Base):
    """
    面试评估报告表
    存储 AI 对面试表现的全面评估，包括分数、亮点、不足和建议
    """
    __tablename__ = "evaluation_reports_history"

    interview_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(InterviewRecordHistory.id),
        unique=True,
        comment="面试记录 ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.id),
        comment="用户标识"
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job.id"),
        comment="岗位ID（强约束主键关联）",
    )
    position_name: Mapped[str] = mapped_column(
        String(50),
        comment="岗位名称"
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        comment="难度等级"
    )
    interview_round: Mapped[int] = mapped_column(
        Integer,
        comment="面试轮次"
    )
    interview_status: Mapped[str] = mapped_column(
        String(50),
        comment="面试状态"
    )
    chat_context: Mapped[str] = mapped_column(
        Text,
        comment="面试过程内容"
    )
    mode: Mapped[str] = mapped_column(
        String(50),
        comment="面试形式"
    )

    # ── 核心评分（原有） ──────────────────────────────────
    content_score: Mapped[float] = mapped_column(
        Float, comment="技术综合分（0-10）：兼容旧版；新版可由技术正确性+知识深度均分回填"
    )
    expression_score: Mapped[float] = mapped_column(Float, comment="表达能力得分（0-10）：整体表达流畅度")
    total_score: Mapped[float] = mapped_column(Float, comment="综合总分（各维度加权平均）")

    # ── 细分技术 / 匹配（新版报告） ───────────────────────
    technical_correctness_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="技术正确性（0-10）：概念与事实是否准确"
    )
    knowledge_depth_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="知识深度（0-10）：原理与底层理解"
    )
    job_match_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="岗位匹配度（0-10）：与目标岗位诉求的契合程度"
    )

    # ── 新增评估维度 ──────────────────────────────────────
    # 注意：如果数据库已存在，需要手动执行 ALTER TABLE 或删除重建数据库：
    # ALTER TABLE evaluation_reports_history ADD COLUMN logic_score REAL DEFAULT 7.0;
    # ALTER TABLE evaluation_reports_history ADD COLUMN communication_score REAL DEFAULT 7.0;
    # ALTER TABLE evaluation_reports_history ADD COLUMN adaptability_score REAL DEFAULT 7.0;
    # ALTER TABLE evaluation_reports_history ADD COLUMN speech_rate_score REAL DEFAULT 7.0;
    # ALTER TABLE evaluation_reports_history ADD COLUMN clarity_score REAL DEFAULT 7.0;
    # ALTER TABLE evaluation_reports_history ADD COLUMN confidence_score REAL DEFAULT 7.0;
    logic_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="逻辑思维得分（0-10）：答题条理性、推理严密性")
    communication_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="沟通表达得分（0-10）：语言组织、表达准确性")
    adaptability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="应变能力得分（0-10）：对难题/追问的应对能力")
    speech_rate_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="语速流畅度得分（0-10）：语速适当、停顿合理")
    clarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="表达清晰度得分（0-10）：语言清晰易懂、无歧义")
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="自信度得分（0-10）：表现出的自信程度")

    highlights: Mapped[str] = mapped_column(Text, comment="亮点：面试中的优秀表现（JSON 列表）")
    weaknesses: Mapped[str] = mapped_column(Text, comment="不足：需要改进的地方（JSON 列表）")
    suggestions: Mapped[str] = mapped_column(Text, comment="改进建议：针对性的学习建议（JSON 列表）")
    # MySQL: ALTER TABLE evaluation_reports_history ADD COLUMN report_markdown TEXT NULL COMMENT 'Markdown 叙事（表格/流程图）';
    report_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Markdown 格式评估叙事")
    report_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="结构化HTML评估报告")
    question_analysis_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="逐题分析JSON数组")
    dimension_feedback_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="维度反馈JSON对象")
    improvement_resources_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="结构化提升资源：知识点、样题、沟通类延伸阅读等"
    )
    rag_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="RAG依据摘要")

    __table_args__ = (
        # get_evaluation_report_by_id 按 interview_id 查询
        Index("idx_erh_interview_id", "interview_id"),
        Index("idx_erh_user_id", "user_id"),
        Index("idx_erh_user_job", "user_id", "job_id"),
    )
