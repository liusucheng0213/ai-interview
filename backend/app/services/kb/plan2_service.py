"""
Plan 2: 岗位查询、岗位-题库绑定、智能题库生成。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.llm_conf import MODEL_INTERVIEW, call_llm
from models.rag_schema import DocumentChunk, Job, Question
from services.kb.rag_plan1 import retrieve_context

QUESTION_PROMPT_TEMPLATE = """你是资深技术面试官，请严格根据给定上下文生成高质量面试题。

要求：
1) 岗位：{job_name}
2) 题目数量：{num}
3) 难度：{difficulty}（easy/medium/hard）
4) 题目必须覆盖岗位核心能力，避免重复，禁止偏离岗位
5) 输出必须是 JSON 数组，不允许 markdown，不允许解释文本

已有题库（避免重复）：
{existing_questions}

RAG 检索上下文（岗位知识 + 题库片段）：
{rag_context}

输出格式：
[
  {{
    "content": "题目内容",
    "answer": "参考答案（80-200字）",
    "difficulty": "easy|medium|hard",
    "exam_point": "考察知识点"
  }}
]
"""


async def bind_job_question(db: AsyncSession, job_id: int, chunk_ids: List[str]) -> None:
    """
    岗位与分块绑定：
    - jobs.main_chunk_id 绑定首个父块
    - document_chunks.job_id 批量绑定
    """
    if not chunk_ids:
        return
    first_chunk_id = chunk_ids[0]
    await db.execute(update(Job).where(Job.id == job_id).values(main_chunk_id=first_chunk_id))
    await db.execute(
        update(DocumentChunk)
        .where(DocumentChunk.chunk_id.in_(chunk_ids))
        .values(job_id=job_id)
    )
    await db.commit()


async def query_jobs_with_rag(
    db: AsyncSession,
    keyword: str,
    with_question: bool = False,
) -> List[Dict[str, Any]]:
    kw = (keyword or "").strip()
    stmt = select(Job)
    if kw:
        stmt = stmt.where(or_(Job.job_name.contains(kw), Job.description.contains(kw)))
    stmt = stmt.order_by(Job.job_name).limit(50)
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    result: List[Dict[str, Any]] = []
    for job in jobs:
        row = {
            "id": job.id,
            "job_name": job.job_name,
            "tech_stack": job.tech_stack if isinstance(job.tech_stack, list) else [],
            "description": job.description or "",
            "main_chunk_id": job.main_chunk_id,
            "related_questions": [],
            "related_knowledge": [],
        }
        if with_question:
            q_hit = await retrieve_context(
                db,
                query=f"{job.job_name} 面试题",
                filter_data={"chunk_type": "question", "job_id": str(job.id)},
            )
            k_hit = await retrieve_context(
                db,
                query=f"{job.job_name} 岗位职责 技术栈",
                filter_data={"chunk_type": "job", "job_id": str(job.id)},
            )
            row["related_questions"] = [c.get("content", "") for c in q_hit.get("chunks", []) if c.get("content")]
            row["related_knowledge"] = [c.get("content", "") for c in k_hit.get("chunks", []) if c.get("content")]
        result.append(row)
    return result


def _safe_parse_questions(raw: str) -> List[Dict[str, Any]]:
    cleaned = (raw or "").strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(cleaned)
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        out.append(
            {
                "content": content,
                "answer": str(item.get("answer", "")).strip(),
                "difficulty": str(item.get("difficulty", "medium")).strip() or "medium",
                "exam_point": str(item.get("exam_point", "")).strip() or "综合能力",
            }
        )
    return out


async def generate_question(
    db: AsyncSession,
    job_id: int,
    num: int = 5,
    difficulty: str = "medium",
) -> List[Dict[str, Any]]:
    """
    生成并入库题目。
    """
    job = await db.get(Job, job_id)
    if not job:
        return []

    existing_stmt = (
        select(Question)
        .where(Question.job_id == job_id)
        .order_by(Question.id.desc())
        .limit(30)
    )
    existing_rows = (await db.execute(existing_stmt)).scalars().all()
    existing_questions = "\n".join([f"- {q.content}" for q in existing_rows]) or "暂无"

    rag = await retrieve_context(
        db,
        query=f"{job.job_name} 面试题 技术考点",
        filter_data={"job_id": str(job_id)},
    )
    rag_context = rag.get("context", "")[:12000] or "暂无知识上下文"

    prompt = QUESTION_PROMPT_TEMPLATE.format(
        job_name=job.job_name,
        num=max(1, min(num, 20)),
        difficulty=difficulty if difficulty in ("easy", "medium", "hard") else "medium",
        existing_questions=existing_questions[:4000],
        rag_context=rag_context,
    )
    raw = await call_llm(
        prompt=prompt,
        system_prompt="你是面试题生成器，只输出 JSON 数组。",
        model=MODEL_INTERVIEW,
    )
    generated = _safe_parse_questions(raw)[: max(1, min(num, 20))]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out: List[Dict[str, Any]] = []
    for g in generated:
        q = Question(
            job_id=job_id,
            content=g["content"],
            answer=g["answer"],
            difficulty=g["difficulty"],
            exam_points=g["exam_point"],
            category="technical",
            generate_time=now,
        )
        db.add(q)
        await db.flush()
        out.append(
            {
                "question_id": q.id,
                "job_id": job_id,
                "content": q.content,
                "answer": q.answer or "",
                "difficulty": q.difficulty or "medium",
                "exam_point": q.exam_points or "",
                "generate_time": now,
            }
        )
    await db.commit()
    return out
