import csv
import io
import logging
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from config.llm_conf import call_llm, MODEL_INTERVIEW
from models.rag_schema import Job as RagJob, Question as RagQuestion
from models.users import User
from services.kb.retrieve import search_knowledge
from services.kb.plan2_service import generate_question
from utils.auth import get_current_user
from utils.enterprise_kb import parse_enterprise_kf_disabled

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/question")

# 导出 CSV 时单岗位条数上限（列表接口默认仍为 2000，互不影响）
_QUESTION_EXPORT_MAX = 10000


async def _list_structured_questions(
    db: AsyncSession,
    position: Optional[str],
    difficulty: Optional[str],
    category: Optional[str],
    *,
    limit: int = 2000,
    offset: int = 0,
) -> List[dict]:
    """结构化题库查询。默认 limit=2000、offset=0，与历史行为一致。单请求硬顶 10000（导出可用满额，列表 Query 仍 le=5000）。"""
    cap = min(max(1, limit), 10000)
    off = max(0, offset)
    stmt = select(RagQuestion, RagJob).join(RagJob, RagQuestion.job_id == RagJob.id)
    if position and position.strip():
        pn = position.strip()
        stmt = stmt.where(or_(RagJob.job_name == pn, RagJob.job_name.contains(pn)))
    if difficulty and str(difficulty).strip():
        stmt = stmt.where(RagQuestion.difficulty == difficulty.strip())
    if category and str(category).strip():
        stmt = stmt.where(RagQuestion.category == category.strip())
    stmt = stmt.order_by(RagQuestion.id.desc()).offset(off).limit(cap)
    result = await db.execute(stmt)
    out: List[dict] = []
    for q, j in result.all():
        out.append(
            {
                "id": q.id,
                "question": q.content,
                "answer": q.answer,
                "difficulty": q.difficulty or "medium",
                "job": j.job_name,
                "type": q.category or "technical",
                "exam_points": q.exam_points or "",
            }
        )
    return out


@router.get("/download", summary="下载题库（结构化）")
async def download_question(
    position: str = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if position and position.strip():
        rows = await _list_structured_questions(
            db, position, None, None, limit=_QUESTION_EXPORT_MAX, offset=0
        )
        positions_to_export = [(position, rows)]
    else:
        jres = await db.execute(select(RagJob.job_name).distinct())
        names = [r[0] for r in jres.all() if r[0]]
        positions_to_export = []
        for name in names:
            rows = await _list_structured_questions(
                db, name, None, None, limit=_QUESTION_EXPORT_MAX, offset=0
            )
            if rows:
                positions_to_export.append((name, rows))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["question", "answer", "difficulty", "category", "exam_points"])
    writer.writeheader()

    for pos_name, rows in positions_to_export:
        for item in rows:
            writer.writerow(
                {
                    "question": item.get("question", ""),
                    "answer": item.get("answer") or "",
                    "difficulty": item.get("difficulty") or "",
                    "category": item.get("type") or "",
                    "exam_points": item.get("exam_points") or "",
                }
            )

    csv_content = output.getvalue().encode("utf-8-sig")
    fn = f"question_bank_{position if position else 'all'}_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )


@router.post("/upload", summary="上传题库（已废弃）")
async def upload_question():
    raise HTTPException(status_code=410, detail="请使用知识库 上传文档")


@router.get("/list", summary="题库列表")
async def get_question_list(
    position: str = None,
    difficulty: str = None,
    category: str = None,
    limit: int = Query(2000, ge=1, le=5000, description="返回条数上限，默认 2000 与旧版一致"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        normalized_position = (position or "").strip()
        if normalized_position:
            job_exists = await db.execute(
                select(RagJob.id).where(or_(RagJob.job_name == normalized_position, RagJob.job_name.contains(normalized_position))).limit(1)
            )
            if not job_exists.scalar_one_or_none():
                return {
                    "status": 200,
                    "message": "该岗位尚未入库，请先上传相关知识文档",
                    "questions": [],
                    "source": "empty",
                }

        structured = await _list_structured_questions(
            db, position, difficulty, category, limit=limit, offset=offset
        )
        if structured:
            return {
                "status": 200,
                "message": f"共 {len(structured)} 道题目",
                "questions": structured,
                "source": "mysql",
            }

        if normalized_position:
            excluded = parse_enterprise_kf_disabled(user)
            hits = await search_knowledge(
                db,
                query=f"{normalized_position} 面试题 考点",
                top_k=10,
                user_id=user.id,
                requester_account_type=getattr(user, "account_type", "personal"),
                retrieval_scope="hybrid",
                excluded_enterprise_kf_ids=excluded,
                position_hint=normalized_position,
            )
            context = "\n\n---\n\n".join((h.get("child_content") or "") for h in hits if h.get("child_content"))
            if not context.strip():
                return {
                    "status": 200,
                    "message": "暂无题目，请先上传知识库文档",
                    "questions": [],
                    "source": "empty",
                }

            prompt = f"""你是资深技术面试官。请基于以下知识片段，生成12 道高质量面试题。
岗位：{normalized_position}
知识片段：
{context[:12000]}

输出严格 JSON 数组，不要 markdown：
[
  {{
    "question": "题目",
    "answer": "参考答案（50-120字）",
    "difficulty": "easy|medium|hard",
    "type": "technical|project|behavior"
  }}
]"""
            raw = await call_llm(prompt=prompt, system_prompt="", model=MODEL_INTERVIEW)
            cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            try:
                generated = json.loads(cleaned)
            except json.JSONDecodeError:
                logger.warning("题库 LLM 返回非合法 JSON，已降级为空列表")
                return {
                    "status": 200,
                    "message": "题目生成失败：模型返回格式异常，请稍后重试",
                    "questions": [],
                    "source": "llm_parse_error",
                }
            if not isinstance(generated, list):
                generated = []
            questions_list = []
            for idx, item in enumerate(generated, start=1):
                if not isinstance(item, dict):
                    continue
                questions_list.append(
                    {
                        "id": f"gen-{idx}",
                        "question": item.get("question", ""),
                        "answer": item.get("answer", ""),
                        "difficulty": item.get("difficulty", "medium"),
                        "job": normalized_position,
                        "type": item.get("type", "technical"),
                        "exam_points": "",
                    }
                )
            return {
                "status": 200,
                "message": f"已根据知识库生成 {len(questions_list)} 道题",
                "questions": questions_list,
                "source": "llm_from_kb",
            }

        return {
            "status": 200,
            "message": "请指定岗位名称以查询题库",
            "questions": [],
            "source": "empty",
        }
    except Exception as e:
        logger.exception("题库列表失败")
        return {"status": 500, "message": f"获取题库失败：{str(e)}", "questions": []}


class GenerateQuestionRequest(BaseModel):
    job_id: int
    num: int = Field(default=5, ge=1, le=20)
    difficulty: str = Field(default="medium")


@router.post("/generate", summary="智能题库生成并入库")
async def generate_question_api(
    body: GenerateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        rows = await generate_question(
            db=db,
            job_id=body.job_id,
            num=body.num,
            difficulty=body.difficulty,
        )
        return {
            "status": 200,
            "message": f"已生成 {len(rows)} 道题",
            "questions": rows,
        }
    except Exception as e:
        logger.exception("生成题库失败")
        raise HTTPException(status_code=500, detail=f"生成题库失败: {e}") from e
