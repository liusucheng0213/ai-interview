from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class InterviewStartRequest(BaseModel):
    """
    开始面试的请求模型

    用于客户端发起新面试时传递必要的参数信息

    Attributes:
        position_name: 岗位名称，如 "Java 后端"、"Web 前端"、"Python 算法"等
                      这个字段是必填项，用于确定面试的技术方向和考察重点
        mode: 面试形式：text（文本）, speech（语音）, video（视频）
        difficulty: 面试难度：entry（入门级）, intermediate（进阶级）, expert（专业级）

    示例:
        {
            "position_name": "Java 后端",
            "mode": "text",
            "difficulty": "entry"
        }
    """
    job_id: int = Field(..., description="岗位ID", examples=[1])
    mode: str = Field(default="text", description="面试形式", examples=["text", "speech", "video"])
    difficulty: str = Field(default="entry", description="面试难度", examples=["entry", "intermediate", "expert"])
    interviewer_style: str = Field(
        default="rigorous",
        description="面试官风格（rigorous/pressure/heuristic）",
        examples=["rigorous", "pressure", "heuristic"],
    )
    language: str = Field(
        default="zh",
        description="面试语言（zh/en/bilingual）",
        examples=["zh", "en", "bilingual"],
    )
    profile_context: Optional[str] = Field(
        default=None,
        description="自定义个人资料摘要（可选，不传则使用账号中的资料自动生成）",
    )
    resume_context: Optional[str] = Field(
        default=None,
        description="自定义简历摘要（可选，不传则使用最近一份简历自动生成）",
    )


class InterviewStartResponse(BaseModel):
    """
    面试回应模型

    用于存储面试中的问题信息

    Attributes:
        question_id: 问题 ID
        content: 问题内容
        answer: 问题的答案
    """
    message: str
    job_id: int
    position_name: str
    difficulty: str
    question: str


class TextAnswerRequest(BaseModel):
    """
    文字回答的请求模型

    用于客户端提交用户对面试问题的文字回答

    Attributes:
        interview_id: 面试记录的唯一标识符（整数类型）
                     用于关联到具体的面试会话
        answer: 用户的文字回答内容
               可以是完整的一句话或多段文字

    示例:
        {
            "interview_id": 1,
            "answer": "我熟悉 Spring Boot 框架，它通过自动配置和起步依赖简化了开发..."
        }
    """
    interview_id: Optional[int] = Field(default=None, description="面试记录 ID（可选，若传须与当前会话一致）")
    answer: str = Field(..., description="用户的文字回答内容", examples=["我熟悉 Spring Boot 框架..."])


class SpeechAnswerRequest(BaseModel):
    """
    语音回答的响应模型
    """
    transcription: str = Field(..., description="语音识别结果")
    next_question: str = Field(..., description="下一个问题")
    analysis: Optional[dict] = Field(None, description="回答分析")


class VideoAnalysisResponse(BaseModel):
    """
    视频分析响应模型
    """
    expression: str = Field(..., description="神态分析")
    psychology: str = Field(..., description="心理状态")
    body_language: str = Field(..., description="肢体语言")
    score: float = Field(..., description="综合评分")
    suggestions: str = Field(..., description="改进建议")
    next_question: Optional[str] = Field(None, description="下一个问题")


class QARecord(BaseModel):
    """问答记录"""
    question: str
    answer: str
    score: Optional[float] = None
    analysis: Optional[str] = None


class DimensionScore(BaseModel):
    """维度得分"""
    name: str
    value: float


class QuestionAnalysisItem(BaseModel):
    question: str
    answer: str
    correctness: str
    completeness: str
    missing_points: List[str]
    errors: List[str]
    feedback: str
    score: float


class EvaluationReportResponse(BaseModel):
    """
    面试评估报告的响应模型

    用于返回 AI 对用户面试表现的全面评估结果
    包含分数、亮点、不足和改进建议
    """
    overall_score: float = Field(..., description="总分（0-10 分）", ge=0, le=10)
    dimension_scores: List[DimensionScore] = Field(..., description="各维度得分")
    qa_records: List[QARecord] = Field(..., description="问答记录")
    highlights: str = Field(..., description="亮点")
    weaknesses: str = Field(..., description="不足")
    suggestions: str = Field(..., description="改进建议")
    report_markdown: Optional[str] = Field(None, description="Markdown 评估叙事（表格/流程图等）")
    report_html: Optional[str] = Field(None, description="结构化HTML评估报告")
    question_analysis: List[QuestionAnalysisItem] = Field(default_factory=list, description="逐题分析数组")
    dimension_feedback: dict = Field(default_factory=dict, description="维度反馈+证据")
    improvement_resources: Optional[Dict[str, Any]] = Field(
        default=None, description="结构化提升资源：知识点、样题、沟通延伸阅读"
    )
    technical_mastery: Optional[float] = Field(default=None, description="技术向综合分（正确性+深度均分或兼容字段）")
    rag_evidence: str = Field(default="", description="RAG证据摘要")


class InterviewDetailResponse(BaseModel):
    """面试详情响应"""
    id: int
    job_id: int
    job: str
    level: str
    time: str
    status: str
    score: float
    report: Optional[EvaluationReportResponse] = None


class InterviewHistoryItem(BaseModel):
    """面试历史项"""
    id: int
    job_id: int
    job: str
    level: str
    time: str
    status: str
    score: Optional[float] = None


class InterviewHistoryResponse(BaseModel):
    """面试历史列表响应"""
    history_list: List[InterviewHistoryItem]


class InterviewStatsResponse(BaseModel):
    """面试统计响应"""
    text_count: int = Field(..., description="文本面试次数")
    speech_count: int = Field(..., description="语音面试次数")
    video_count: int = Field(..., description="视频面试次数")
    question_count: int = Field(..., description="面试试题次数")
