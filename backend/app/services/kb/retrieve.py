"""RAG 3.0 统一检索适配层（兼容历史调用方返回结构）。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.rag_schema import Job, Question
from services.kb.rag_plan1 import retrieve_context


async def search_knowledge(
    db: AsyncSession,
    query: str,
    top_k: int = 8,
    user_id: Optional[int] = None,
    requester_account_type: str = "personal",
    retrieval_scope: str = "hybrid",
    excluded_enterprise_kf_ids: Optional[Set[int]] = None,
    file_id: Optional[int] = None,
    position_hint: Optional[str] = None,
) -> List[Dict[str, Any]]:
    _ = (user_id, requester_account_type, retrieval_scope, excluded_enterprise_kf_ids, file_id)
    rag = await retrieve_context(
        db=db,
        query=f"{(position_hint or '').strip()} {query}".strip() or query,
        filter_data=None,
    )
    rag_chunks = rag.get("chunks", [])[: max(top_k, 1)]
    out: List[Dict[str, Any]] = [
        {
            "distance": max(0.0, 1.0 - float(c.get("score", 0.0))),
            "child_content": c.get("content") or "",
            "chunk_id": c.get("chunk_id"),
            "parent_id": c.get("parent_id"),
            "file_id": None,
            "chunk_type": c.get("chunk_type", "other"),
            "parent_title": c.get("chunk_type", "知识库"),
            "parent_preview": "",
            "source_filename": "",
            "parse_status": "done",
            "related_questions": [],
            "result_kind": "知识库",
            "source_type": "知识库",
        }
        for c in rag_chunks
    ]

    q_hits: List[Dict[str, Any]] = []
    terms = [t for t in re.split(r"[\s\u3000,，;；]+", query) if len(t) >= 2][:8]
    if position_hint and position_hint.strip():
        stmt = select(Question, Job).join(Job, Question.job_id == Job.id).where(Job.job_name == position_hint.strip())
        if terms:
            stmt = stmt.where(or_(*[Question.content.contains(t) for t in terms]))
        q_res = await db.execute(stmt.order_by(Question.id.desc()).limit(max(top_k, 6)))
        for q, j in q_res.all():
            q_hits.append(
                {
                    "distance": 0.0,
                    "child_content": q.content or "",
                    "chunk_id": str(q.id),
                    "parent_id": None,
                    "file_id": q.source_file_id,
                    "parent_title": q.exam_points or (q.category or "面试题"),
                    "parent_preview": q.answer or "",
                    "source_filename": "",
                    "parse_status": "done",
                    "related_questions": [],
                    "result_kind": "题库",
                    "source_type": "题库",
                    "job_name": j.job_name,
                    "question_id": q.id,
                    "answer": q.answer or "",
                    "exam_points": q.exam_points or "",
                    "category": q.category or "",
                    "difficulty": q.difficulty or "",
                }
            )

    merged = q_hits + out
    deduped: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for item in merged:
        key = (item.get("child_content") or "").strip()[:180]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= top_k * 2:
            break
    return deduped
