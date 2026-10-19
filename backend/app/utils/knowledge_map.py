"""基于 job / question / 向量检索构建文字版岗位知识图谱数据。"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.rag_schema import Job, KbParentChunk, Question
from models.users import User
from services.kb.retrieve import search_knowledge
from utils.enterprise_kb import parse_enterprise_kf_disabled


async def build_job_knowledge_map(
    db: AsyncSession,
    user: User,
    job_name: str,
    query_hint: str = "",
) -> Dict[str, Any]:
    """岗位 → 技术栈 → 知识点（父块标题）→ 面试题 → 检索片段。"""
    name = (job_name or "").strip()
    if not name:
        return {"ok": False, "message": "岗位不能为空", "job": None, "layers": []}

    jres = await db.execute(select(Job).where(Job.job_name == name))
    job = jres.scalar_one_or_none()
    if not job:
        jres2 = await db.execute(select(Job).where(Job.job_name.contains(name)).limit(1))
        job = jres2.scalar_one_or_none()

    tech: List[str] = []
    if job and isinstance(job.tech_stack, list):
        tech = [str(x) for x in job.tech_stack if x][:24]
    elif job and isinstance(job.tech_stack, dict):
        tech = [str(v) for v in job.tech_stack.values() if v][:24]

    layers: List[Dict[str, Any]] = []
    if job:
        qres = await db.execute(
            select(Question)
            .where(Question.job_id == job.id)
            .order_by(Question.id.desc())
            .limit(80)
        )
        questions = qres.scalars().all()
        by_ep: Dict[str, List[Dict[str, Any]]] = {}
        for q in questions:
            ep = (q.exam_points or "").strip() or (q.category or "").strip() or "综合考点"
            if ep not in by_ep:
                by_ep[ep] = []
            if len(by_ep[ep]) < 12:
                by_ep[ep].append(
                    {
                        "id": q.id,
                        "content": (q.content or "")[:800],
                        "answer_preview": (q.answer or "")[:400],
                        "difficulty": q.difficulty or "",
                    }
                )

        parent_titles: List[str] = []
        if questions:
            fids = list({q.source_file_id for q in questions if q.source_file_id})[:12]
            for fid in fids:
                pres = await db.execute(
                    select(KbParentChunk.title)
                    .where(KbParentChunk.knowledge_file_id == fid)
                    .order_by(KbParentChunk.sort_order)
                    .limit(40)
                )
                for (t,) in pres.all():
                    if t and t not in parent_titles:
                        parent_titles.append(t)
                if len(parent_titles) >= 30:
                    break

        qh = query_hint or " ".join(tech[:5]) or name
        kb_snippets: List[Dict[str, str]] = []
        try:
            excluded = parse_enterprise_kf_disabled(user)
            hits = await search_knowledge(
                db,
                query=f"{name} {qh}"[:500],
                top_k=6,
                user_id=user.id,
                requester_account_type=getattr(user, "account_type", "personal"),
                retrieval_scope="hybrid",
                excluded_enterprise_kf_ids=excluded,
                position_hint=name,
            )
            for h in hits[:6]:
                fn = h.get("source_filename") or ""
                kb_snippets.append(
                    {
                        "parent_title": (h.get("parent_title") or "")[:200],
                        "snippet": (h.get("child_content") or "")[:600],
                        "filename": fn[:180],
                        "file_id": h.get("file_id"),
                    }
                )
        except Exception:
            pass

        layers.append(
            {
                "level": "tech_stack",
                "title": "技术栈",
                "items": [{"label": t, "kind": "tech"} for t in tech]
                or [{"label": "（可在知识库文档中维护岗位技术栈）", "kind": "placeholder"}],
            }
        )
        layers.append(
            {
                "level": "knowledge_points",
                "title": "知识点文档（父块）",
                "items": [{"label": x, "kind": "kb_parent"} for x in parent_titles[:24]]
                or [{"label": "（解析入库后将展示父块标题）", "kind": "placeholder"}],
            }
        )

        for ep, qs in list(by_ep.items())[:16]:
            layers.append(
                {
                    "level": "topic",
                    "title": ep,
                    "items": qs,
                    "kind": "questions",
                }
            )

        if kb_snippets:
            layers.append(
                {
                    "level": "vector_snippets",
                    "title": "知识库检索摘录（子块）",
                    "items": kb_snippets,
                    "kind": "kb_snippets",
                }
            )

        return {
            "ok": True,
            "job": {
                "id": job.id,
                "job_name": job.job_name,
                "tech_stack": tech,
                "description": (job.description or "")[:2000],
            },
            "layers": layers,
        }

    return {
        "ok": False,
        "message": "未在 job 表中找到该岗位",
        "job": None,
        "layers": [],
    }
