"""
面试历史 CRUD 层

优化说明：
- search_now_history：优先走 Redis 缓存（interview_id），命中后 PK 查询，避免全表扫描
- add_rd：优先使用 Redis 中缓存的 interview_id 做 PK 查询，避免全表扫描
- add_content_history：接受可选的 history 参数，调用方可传入已有对象
  避免内部重复调用 search_now_history；同时返回更新后的 history 对象
  供路由层复用，省去 fresh_history 的额外查询
"""
import json
import logging
from typing import Any, Dict, Optional, Union

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from cache.history import (
    get_current_interview_id,
    set_current_interview_id,
    invalidate_current_interview,
)
from models.history import EvaluationReportHistory, InterviewRecordHistory
from models.users import User

logger = logging.getLogger(__name__)


def _serialize_list(value) -> str:
    """将列表或字符串序列化为 JSON 字符串存入 Text 列"""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return str(value) if value is not None else "[]"


def _serialize_improvement_resources(raw) -> Optional[str]:
    if not isinstance(raw, dict):
        return None
    if not any(raw.get(k) for k in ("knowledge_points", "sample_interview_questions", "communication_readings")):
        return None
    return json.dumps(raw, ensure_ascii=False)


def _deserialize_list(value) -> list:
    """将 Text 列中的 JSON 字符串反序列化为列表"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else [result]
    except (json.JSONDecodeError, TypeError):
        return [value] if value else []


def _safe_dimension_feedback(raw: Union[str, dict, None]) -> dict:
    """解析维度反馈 JSON，损坏或异常时返回空 dict，避免详情接口 500。"""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _safe_improvement_resources(raw: Union[str, dict, None]) -> Optional[dict]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw if any(raw.values()) else None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def dimension_scores_from_values(
    *,
    content_score: Optional[float],
    technical_correctness_score: Optional[float],
    knowledge_depth_score: Optional[float],
    logic_score: Optional[float],
    job_match_score: Optional[float],
    communication_score: Optional[float],
    adaptability_score: Optional[float],
    speech_rate_score: Optional[float],
    clarity_score: Optional[float],
    confidence_score: Optional[float],
    expression_score: Optional[float],
    resume_match_score: Optional[float] = None,
) -> list:
    """
    构建雷达/条形图用维度列表（0–10），顺序稳定；不含「综合得分」以免与总分重复。
    旧报告仅有 content_score 时退化为单一「技术知识」维度。
    """
    rows: list[dict] = []
    tc = technical_correctness_score
    kd = knowledge_depth_score
    cs = content_score

    if tc is not None:
        rows.append({"name": "技术正确性", "value": round(float(tc), 2)})
    if kd is not None:
        rows.append({"name": "知识深度", "value": round(float(kd), 2)})
    if tc is None and kd is None and cs is not None:
        rows.append({"name": "技术知识", "value": round(float(cs), 2)})

    for attr_val, label in (
        (logic_score, "逻辑思维"),
        (job_match_score, "岗位匹配"),
        (communication_score, "沟通表达"),
        (adaptability_score, "应变能力"),
        (clarity_score, "表达清晰度"),
        (confidence_score, "自信度"),
        (speech_rate_score, "语速流畅"),
        (expression_score, "综合表达"),
    ):
        if attr_val is not None:
            rows.append({"name": label, "value": round(float(attr_val), 2)})
    if resume_match_score is not None:
        rows.append({"name": "简历匹配", "value": round(float(resume_match_score), 2)})
    return rows


async def create_history(user: User, job_id: int, position_name: str, difficulty: str, mode: str, db: AsyncSession):
    # 开始新面试前清除旧缓存
    await invalidate_current_interview(user.id)

    history = InterviewRecordHistory(
        user_id=user.id,
        job_id=job_id,
        position_name=position_name,
        difficulty=difficulty,
        interview_round=1,
        mode=mode,
        interview_status="面试中",
        chat_context="",
    )
    db.add(history)
    await db.commit()
    await db.refresh(history)

    await set_current_interview_id(user.id, history.id)
    return history


async def search_now_history(user: User, db: AsyncSession) -> Optional[InterviewRecordHistory]:
    """
    查询用户当前进行中的面试。
    优先走 Redis 缓存（interview_id），命中后通过 PK 查询；
    缓存未命中时回退到带索引的条件查询。
    """
    # 1. Redis 缓存
    cached_id = await get_current_interview_id(user.id)
    if cached_id:
        q = await db.execute(
            select(InterviewRecordHistory).where(InterviewRecordHistory.id == cached_id)
        )
        result = q.scalar_one_or_none()
        if result and result.interview_status == "面试中":
            logger.debug(f"[Cache] 当前面试缓存命中，interview_id={cached_id}")
            return result
        await invalidate_current_interview(user.id)

    # 2. 数据库查询（利用 idx_irh_user_status 复合索引）
    q = await db.execute(
        select(InterviewRecordHistory)
        .where(
            InterviewRecordHistory.user_id == user.id,
            InterviewRecordHistory.interview_status == "面试中",
        )
    )
    result = q.scalar_one_or_none()

    if result:
        logger.info(f"[CRUD] 找到面试 ID={result.id}，岗位={result.position_name}，轮次={result.interview_round}")
        await set_current_interview_id(user.id, result.id)
    else:
        logger.warning(f"[CRUD] 用户 {user.id} 无进行中面试")

    return result


async def search_rd(user: User, db: AsyncSession, job_id: Optional[int] = None) -> int:
    """返回当前进行中面试的轮次，无进行中面试时返回 0。传入 job_id 时仅当进行中面试属于该岗位才返回轮次。"""
    cached_id = await get_current_interview_id(user.id)
    if cached_id:
        q = await db.execute(
            select(InterviewRecordHistory).where(InterviewRecordHistory.id == cached_id)
        )
        result = q.scalar_one_or_none()
        if result and result.interview_status == "面试中":
            if job_id is not None and result.job_id != job_id:
                return 0
            return result.interview_round

    q = await db.execute(
        select(InterviewRecordHistory)
        .where(
            InterviewRecordHistory.user_id == user.id,
            InterviewRecordHistory.interview_status == "面试中",
        )
    )
    result = q.scalar_one_or_none()
    if not result:
        return 0
    if job_id is not None and result.job_id != job_id:
        return 0
    return result.interview_round


async def add_rd(user: User, db: AsyncSession) -> int:
    """
    将当前面试轮次 +1，返回新轮次。
    优先使用 Redis 缓存的 interview_id 做 PK 查询，避免全表扫描。
    """
    cached_id = await get_current_interview_id(user.id)
    if cached_id:
        q = await db.execute(
            select(InterviewRecordHistory).where(InterviewRecordHistory.id == cached_id)
        )
        result = q.scalar_one_or_none()
        if result and result.interview_status == "面试中":
            result.interview_round += 1
            rd = result.interview_round
            await db.commit()
            await db.refresh(result)
            return rd

    # fallback：全表条件查询
    q = await db.execute(
        select(InterviewRecordHistory)
        .where(
            InterviewRecordHistory.user_id == user.id,
            InterviewRecordHistory.interview_status == "面试中",
        )
    )
    result = q.scalar_one_or_none()
    if not result:
        return 1
    result.interview_round += 1
    rd = result.interview_round
    await db.commit()
    await db.refresh(result)
    return rd


async def add_content_history(
    user: User,
    content: str,
    db: AsyncSession,
    history: Optional[InterviewRecordHistory] = None,
) -> Optional[InterviewRecordHistory]:
    """
    向当前面试记录追加内容。

    Args:
        history: 调用方已有的面试对象（可省去内部重复查询）。
                 未传入时自动查询。

    Returns:
        更新后的面试对象（供调用方继续复用），失败时返回 None。
    """
    if history is None:
        history = await search_now_history(user, db)

    if not history:
        logger.warning(f"[CRUD] 用户 {user.id} 无进行中面试，无法追加内容")
        return None

    logger.debug(f"[CRUD] 追加内容，长度：{len(content)}")
    history.chat_context += content
    await db.commit()
    return history


async def get_user_history(user: User, job_id: int, db: AsyncSession):
    """获取用户指定岗位的已结束面试历史记录（强隔离，不回退）。"""
    q = await db.execute(
        select(InterviewRecordHistory)
        .where(
            InterviewRecordHistory.user_id == user.id,
            InterviewRecordHistory.job_id == job_id,
            InterviewRecordHistory.interview_status == "面试结束",
        )
    )
    return q.scalars().all()


async def get_interview_by_id(interview_id: int, db: AsyncSession):
    """根据 ID 获取面试详情"""
    q = await db.execute(
        select(InterviewRecordHistory).where(InterviewRecordHistory.id == interview_id)
    )
    return q.scalar_one_or_none()


async def get_evaluation_report_by_id(interview_id: int, db: AsyncSession):
    """根据面试 ID 获取评估报告"""
    q = await db.execute(
        select(EvaluationReportHistory).where(EvaluationReportHistory.interview_id == interview_id)
    )
    return q.scalar_one_or_none()


def build_interview_detail_payload(history: InterviewRecordHistory, report: Optional[EvaluationReportHistory]) -> Dict[str, Any]:
    """
    构建与 GET /api/interview/detail/{id} 一致的面试详情结构（含问答与维度得分）。
    供求职者端与企业端共用。
    """
    difficulty_label = {"entry": "入门级", "intermediate": "进阶级", "expert": "专业级"}.get(
        history.difficulty, history.difficulty
    )
    interview_data: Dict[str, Any] = {
        "id": history.id,
        "job_id": history.job_id,
        "job": history.position_name,
        "level": difficulty_label,
        "time": str(history.credited_at) if hasattr(history, "credited_at") else "未知时间",
        "status": history.interview_status,
        "score": report.total_score if report else 0,
        "report": None,
    }
    if not report:
        return interview_data

    qa_records = []
    if history.chat_context:
        lines = [ln for ln in history.chat_context.strip().split("\n") if ln.strip()]
        if lines and lines[0].startswith("[SESSION_META]"):
            lines = lines[1:]
        for i in range(0, len(lines) - 1, 2):
            if i + 1 < len(lines):
                q_line = lines[i]
                if not (q_line.startswith("ai面试官：") or q_line.startswith("面试官：")):
                    continue
                raw_answer = lines[i + 1]
                j = i + 2
                while j < len(lines) and not lines[j].startswith("ai面试官：") and not lines[j].startswith("面试官："):
                    raw_answer += " " + lines[j]
                    j += 1
                qa_records.append({
                    "question": q_line.replace("ai面试官：", "").replace("面试官：", ""),
                    "answer": raw_answer
                        .replace("候选人：", "")
                        .replace("候选人（语音）：", "")
                        .replace("候选人（视频）：", "")
                        .replace("表情分析：", "[表情] ")
                        .replace("心理状态：", "[状态] ")
                        .replace("肢体语言：", "[肢体] ")
                        .replace("回答内容：", "")
                        .strip(),
                })

    dim_scores = dimension_scores_from_values(
        content_score=float(report.content_score) if report.content_score is not None else None,
        technical_correctness_score=getattr(report, "technical_correctness_score", None),
        knowledge_depth_score=getattr(report, "knowledge_depth_score", None),
        logic_score=getattr(report, "logic_score", None),
        job_match_score=getattr(report, "job_match_score", None),
        communication_score=getattr(report, "communication_score", None),
        adaptability_score=getattr(report, "adaptability_score", None),
        speech_rate_score=getattr(report, "speech_rate_score", None),
        clarity_score=getattr(report, "clarity_score", None),
        confidence_score=getattr(report, "confidence_score", None),
        expression_score=float(report.expression_score) if report.expression_score is not None else None,
        resume_match_score=None,
    )

    tc = getattr(report, "technical_correctness_score", None)
    kd = getattr(report, "knowledge_depth_score", None)
    if tc is not None and kd is not None:
        technical_mastery = (float(tc) + float(kd)) / 2.0
    elif tc is not None:
        technical_mastery = float(tc)
    elif kd is not None:
        technical_mastery = float(kd)
    else:
        technical_mastery = float(report.content_score) if report.content_score is not None else None

    interview_data["report"] = {
        "overall_score": report.total_score,
        "technical_mastery": technical_mastery,
        "dimension_scores": dim_scores,
        "qa_records": qa_records,
        "highlights": _deserialize_list(report.highlights),
        "weaknesses": _deserialize_list(report.weaknesses),
        "suggestions": _deserialize_list(report.suggestions),
        "report_markdown": getattr(report, "report_markdown", None) or None,
        "report_html": getattr(report, "report_html", None) or None,
        "question_analysis": _deserialize_list(getattr(report, "question_analysis_json", None)),
        "dimension_feedback": _safe_dimension_feedback(getattr(report, "dimension_feedback_json", None)),
        "improvement_resources": _safe_improvement_resources(
            getattr(report, "improvement_resources_json", None)
        ),
        "rag_evidence": getattr(report, "rag_evidence", None) or "",
    }
    return interview_data


async def count_interviews_by_mode(user: User, db: AsyncSession, mode: Optional[str] = None) -> int:
    """统计用户面试次数"""
    q = select(func.count()).select_from(InterviewRecordHistory).where(
        InterviewRecordHistory.user_id == user.id,
        InterviewRecordHistory.interview_status == "面试结束",
    )
    result = await db.execute(q)
    return result.scalar()


async def create_assessment(user: User, content: dict, db: AsyncSession):
    history = await search_now_history(user, db)
    if not history:
        logger.info(f"[CRUD] 用户 {user.id} 无进行中面试")
        return None

    history.interview_status = "面试结束"
    await db.commit()
    await db.refresh(history)

    await invalidate_current_interview(user.id)

    assessment = EvaluationReportHistory(
        interview_id=history.id,
        user_id=history.user_id,
        job_id=history.job_id,
        position_name=history.position_name,
        difficulty=history.difficulty,
        interview_round=history.interview_round,
        interview_status="面试结束",
        chat_context=history.chat_context,
        mode=history.mode,
        content_score=content['content_score'],
        expression_score=content['expression_score'],
        total_score=content['total_score'],
        logic_score=content.get('logic_score'),
        job_match_score=content.get('job_match_score'),
        technical_correctness_score=content.get('technical_correctness_score'),
        knowledge_depth_score=content.get('knowledge_depth_score'),
        communication_score=content.get('communication_score'),
        adaptability_score=content.get('adaptability_score'),
        speech_rate_score=content.get('speech_rate_score'),
        clarity_score=content.get('clarity_score'),
        confidence_score=content.get('confidence_score'),
        highlights=_serialize_list(content['highlights']),
        weaknesses=_serialize_list(content['weaknesses']),
        suggestions=_serialize_list(content['suggestions']),
        report_markdown=content.get("report_markdown"),
        report_html=content.get("report_html"),
        question_analysis_json=_serialize_list(content.get("question_analysis", [])),
        dimension_feedback_json=json.dumps(content.get("dimension_feedback", {}), ensure_ascii=False),
        improvement_resources_json=_serialize_improvement_resources(
            content.get("improvement_resources")
        ),
        rag_evidence=content.get("rag_evidence"),
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment
