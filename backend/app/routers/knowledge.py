"""
知识库：上传 → 解析 → 结构化入库 → 父子分块 → 子块向量（Chroma）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import config.rag_conf as rag_conf
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import AsyncSessionLocal, get_db
from models.rag_schema import Document, DocumentChunk, Job, KnowledgeFile, KbChildChunk, KbParentChunk, Question
from models.users import User
from services.kb.chroma_child import delete_children_by_file_id
from services.kb.ingest_pipeline import run_ingest_for_file
from services.kb.retrieve import search_knowledge
from services.kb.rag_plan1 import retrieve_context
from utils.auth import get_current_user
from utils.enterprise_kb import parse_enterprise_kf_disabled, serialize_enterprise_kf_disabled
from utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".doc", ".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE = 20 * 1024 * 1024
STORAGE_ROOT = Path("./storage/knowledge")


def _user_dir(user_id: int) -> Path:
    d = STORAGE_ROOT / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_uploaded_bytes(file_bytes: bytes, user_id: int, filename: str) -> str:
    user_dir = _user_dir(user_id)
    target = user_dir / filename
    if target.exists():
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        stem, suf = Path(filename).stem, Path(filename).suffix
        target = user_dir / f"{stem}_{ts}{suf}"
    target.write_bytes(file_bytes)
    return str(target.relative_to(STORAGE_ROOT.parent))


def _resolve_path(storage_path: str) -> Path:
    p = Path(storage_path)
    if not p.is_absolute():
        p = Path(".") / p
    if not p.exists():
        alt = Path("./storage") / storage_path
        if alt.exists():
            return alt
    return p


async def _bg_ingest(file_id: int) -> None:
    async with AsyncSessionLocal() as db:
        try:
            await run_ingest_for_file(db, file_id)
        except Exception:
            logger.exception("[KB] 后台入库失败 file_id=%s", file_id)


class SearchBody(BaseModel):
    query: str
    top_k: int = Field(default=8, ge=1, le=30)
    file_id: Optional[int] = None
    position_hint: Optional[str] = Field(default=None, description="当前岗位，用于优先召回该岗位题库与知识库")


class EnterpriseFileRetrievalBody(BaseModel):
    enabled: bool = True


@router.get("/stats", summary="向量库统计")
async def knowledge_stats(_user: User = Depends(get_current_user)):
    n = 0
    col = rag_conf.child_collection
    if col is not None:
        try:
            n = col.count()
        except Exception:
            pass
    return success_response(
        message="ok",
        data={
            "child_chunks": n,
            "embedding_ok": rag_conf.embedding_model is not None,
        },
    )


@router.post("/upload", summary="上传文件（异步解析与向量化）")
async def upload_knowledge(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(default="unified"),
    description: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的类型 {ext}，支持：{', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件超过 20MB")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="文件为空")

    storage_path = _save_uploaded_bytes(file_bytes, user.id, filename)
    visibility = "enterprise_global" if getattr(user, "account_type", "personal") == "enterprise" else "user_local"
    org_id = (getattr(user, "company_code", None) or "").strip() or None

    kf = KnowledgeFile(
        user_id=user.id,
        original_filename=filename,
        storage_path=storage_path,
        file_type=ext.lstrip(".") or "bin",
        # 单库模式：统一写入 unified，避免通用/岗位分流语义
        category="unified",
        description=(description or None),
        parse_status="pending",
        visibility=visibility,
        org_id=org_id,
    )
    db.add(kf)
    await db.commit()
    await db.refresh(kf)

    background_tasks.add_task(_bg_ingest, kf.id)
    logger.info("[KB] 已排队入库 file_id=%s", kf.id)

    return success_response(
        message="已接收文件，后台解析中",
        data={"file_id": kf.id, "filename": filename, "parse_status": kf.parse_status},
    )


@router.get("/files", summary="文件列表")
async def list_knowledge_files(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    disabled_kf = parse_enterprise_kf_disabled(user)

    if getattr(user, "account_type", "personal") == "enterprise":
        stmt = select(KnowledgeFile).where(KnowledgeFile.user_id == user.id).order_by(KnowledgeFile.credited_at.desc())
    else:
        stmt = (
            select(KnowledgeFile)
            .join(User, KnowledgeFile.user_id == User.id)
            .where(
                or_(
                    KnowledgeFile.user_id == user.id,
                    KnowledgeFile.visibility == "enterprise_global",
                )
            )
            .order_by(KnowledgeFile.credited_at.desc())
        )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    out = []
    for kf in rows:
        owner = await db.get(User, kf.user_id)
        uploader_ent = bool(owner and getattr(owner, "account_type", "personal") == "enterprise")
        is_own = kf.user_id == user.id
        is_ent_shared = uploader_ent and not is_own
        retrieval_enabled = True
        if getattr(user, "account_type", "personal") == "personal" and is_ent_shared:
            retrieval_enabled = kf.id not in disabled_kf
        out.append(
            {
                "id": kf.id,
                "filename": kf.original_filename,
                "file_type": kf.file_type,
                "category": kf.category,
                "description": kf.description or "",
                "parse_status": kf.parse_status,
                "parse_message": (kf.parse_message or "")[:500],
                "char_count": kf.char_count,
                "parent_chunk_count": kf.parent_chunk_count,
                "child_chunk_count": kf.child_chunk_count,
                "created_at": str(kf.credited_at) if kf.credited_at else "",
                "visibility": kf.visibility,
                "is_enterprise_shared": is_ent_shared,
                "is_own": is_own,
                "uploader_username": owner.username if owner else "",
                "retrieval_enabled": retrieval_enabled,
            }
        )

    return success_response(message="ok", data={"files": out, "total": len(out)})


@router.get("/files/{file_id}", summary="文件元信息")
async def get_knowledge_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kf = await db.get(KnowledgeFile, file_id)
    if not kf:
        raise HTTPException(status_code=404, detail="文件不存在")
    owner = await db.get(User, kf.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="记录异常")
    if getattr(user, "account_type", "personal") == "enterprise":
        if kf.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看")
    else:
        uploader_ent = getattr(owner, "account_type", "personal") == "enterprise"
        if kf.user_id != user.id and not (uploader_ent and kf.visibility == "enterprise_global"):
            raise HTTPException(status_code=403, detail="无权查看")

    return success_response(
        message="ok",
        data={
            "id": kf.id,
            "filename": kf.original_filename,
            "file_type": kf.file_type,
            "category": kf.category,
            "description": kf.description or "",
            "parse_status": kf.parse_status,
            "parse_message": kf.parse_message or "",
            "char_count": kf.char_count,
            "parent_chunk_count": kf.parent_chunk_count,
            "child_chunk_count": kf.child_chunk_count,
            "created_at": str(kf.credited_at) if kf.credited_at else "",
        },
    )


@router.get("/files/{file_id}/detail", summary="文件详情（岗位、题目、父块）")
async def get_knowledge_detail(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kf = await db.get(KnowledgeFile, file_id)
    if not kf:
        raise HTTPException(status_code=404, detail="文件不存在")
    owner = await db.get(User, kf.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="记录异常")
    if getattr(user, "account_type", "personal") == "enterprise":
        if kf.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权查看")
    else:
        uploader_ent = getattr(owner, "account_type", "personal") == "enterprise"
        if kf.user_id != user.id and not (uploader_ent and kf.visibility == "enterprise_global"):
            raise HTTPException(status_code=403, detail="无权查看")

    jres = await db.execute(select(Job).where(Job.source_file_id == file_id))
    jobs = jres.scalars().all()
    jobs_out = []
    for j in jobs:
        ts = j.tech_stack
        if isinstance(ts, list):
            tech = ts
        elif isinstance(ts, dict):
            tech = list(ts.values()) if ts else []
        else:
            tech = []
        jobs_out.append(
            {"id": j.id, "job_name": j.job_name, "tech_stack": tech, "description": j.description or ""}
        )

    qres = await db.execute(select(Question).where(Question.source_file_id == file_id))
    qs = qres.scalars().all()
    questions_out = [
        {
            "id": q.id,
            "content": q.content,
            "answer": q.answer,
            "difficulty": q.difficulty,
            "exam_points": q.exam_points,
            "category": q.category,
            "job_id": q.job_id,
        }
        for q in qs
    ]

    pres = await db.execute(
        select(KbParentChunk)
        .where(KbParentChunk.knowledge_file_id == file_id)
        .order_by(KbParentChunk.sort_order)
    )
    parents = pres.scalars().all()
    parents_out = [
        {
            "id": p.id,
            "title": p.title,
            "source_kind": p.source_kind,
            "source_row": p.source_row,
            "preview": p.preview or "",
        }
        for p in parents
    ]

    exam_points = sorted({(q.exam_points or "").strip() for q in qs if (q.exam_points or "").strip()})

    return success_response(
        message="ok",
        data={
            "file": {
                "id": kf.id,
                "filename": kf.original_filename,
                "parse_status": kf.parse_status,
                "created_at": str(kf.credited_at) if kf.credited_at else "",
            },
            "jobs": jobs_out,
            "questions": questions_out,
            "parent_chunks": parents_out,
            "exam_points_summary": exam_points[:200],
        },
    )


@router.delete("/files/{file_id}", summary="删除文件及向量")
async def delete_knowledge_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kf = await db.get(KnowledgeFile, file_id)
    if not kf:
        raise HTTPException(status_code=404, detail="文件不存在")
    if kf.user_id != user.id:
        raise HTTPException(status_code=403, detail="只能删除本人上传的文件")

    delete_children_by_file_id(file_id)
    await db.execute(delete(KbChildChunk).where(KbChildChunk.knowledge_file_id == file_id))
    await db.execute(delete(KbParentChunk).where(KbParentChunk.knowledge_file_id == file_id))

    p = _resolve_path(kf.storage_path)
    try:
        if p.exists():
            p.unlink()
    except Exception as e:
        logger.warning("[KB] 删除本地文件失败 %s: %s", p, e)

    await db.execute(delete(KnowledgeFile).where(KnowledgeFile.id == file_id))
    await db.commit()
    return success_response(message="已删除", data={"file_id": file_id})


@router.post("/search", summary="语义检索")
async def search_knowledge_api(
    body: SearchBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    excluded_kf = parse_enterprise_kf_disabled(user)
    pos = (body.position_hint or "").strip()
    q = body.query.strip()
    merged: List[dict] = []
    seen_q: set = set()
    q_for_vec = f"{pos} {q}".strip() if pos else q
    hits = await search_knowledge(
        db,
        query=q_for_vec,
        top_k=body.top_k,
        user_id=user.id,
        requester_account_type=getattr(user, "account_type", "personal"),
        retrieval_scope="hybrid",
        excluded_enterprise_kf_ids=excluded_kf,
        file_id=body.file_id,
        position_hint=pos if pos else None,
    )
    for h in hits:
        ck = (h.get("child_content") or "")[:120]
        if ck and ck in seen_q:
            continue
        if ck:
            seen_q.add(ck)
        merged.append(h)

    return success_response(
        message="ok",
        data={"results": merged[: body.top_k * 2], "total": len(merged), "position_applied": bool(pos)},
    )


@router.get("/job-map", summary="文字版岗位知识图谱（层级数据）")
async def job_knowledge_map(
    job_name: str = "",
    q: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from utils.knowledge_map import build_job_knowledge_map

    if not (job_name or "").strip():
        raise HTTPException(status_code=400, detail="job_name 不能为空")
    data = await build_job_knowledge_map(db, user, job_name.strip(), query_hint=(q or "").strip())
    return success_response(message="ok", data=data)


@router.put("/enterprise-file/{file_id}/retrieval", summary="求职者：企业共享文件是否参与检索")
async def set_enterprise_file_retrieval(
    file_id: int,
    body: EnterpriseFileRetrievalBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if getattr(user, "account_type", "personal") != "personal":
        raise HTTPException(status_code=403, detail="仅求职者账号可调整")

    kf = await db.get(KnowledgeFile, file_id)
    if not kf:
        raise HTTPException(status_code=404, detail="文件不存在")
    owner = await db.get(User, kf.user_id)
    if not owner or getattr(owner, "account_type", "personal") != "enterprise":
        raise HTTPException(status_code=400, detail="非企业共享文件")
    if kf.user_id == user.id:
        raise HTTPException(status_code=400, detail="请对非本人上传的企业文件使用此开关")
    if kf.visibility != "enterprise_global":
        raise HTTPException(status_code=400, detail="该文件非企业全局共享")

    disabled = parse_enterprise_kf_disabled(user)
    if body.enabled:
        disabled.discard(file_id)
    else:
        disabled.add(file_id)

    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(enterprise_kf_disabled_json=serialize_enterprise_kf_disabled(disabled))
    )
    await db.commit()
    return success_response(
        message="检索偏好已更新",
        data={"retrieval_enabled": body.enabled, "file_id": file_id},
    )


@router.get("/jobs", summary="岗位列表")
async def list_jobs(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    _ = user
    result = await db.execute(select(Job).order_by(Job.job_name))
    jobs = result.scalars().all()
    out = []
    for j in jobs:
        ts = j.tech_stack
        if isinstance(ts, list):
            tech = ts
        elif isinstance(ts, dict):
            tech = list(ts.values()) if ts else []
        else:
            tech = []
        out.append(
            {
                "id": j.id,
                "job_name": j.job_name,
                "tech_stack": tech,
                "description": (j.description or "")[:2000],
                "source_file_id": j.source_file_id,
            }
        )
    return success_response(message="ok", data={"jobs": out, "total": len(out)})


@router.get("/questions", summary="题库筛选")
async def list_questions_api(
    job_id: Optional[int] = None,
    job_name: Optional[str] = None,
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ = user
    stmt = select(Question, Job).join(Job, Question.job_id == Job.id)
    if job_id is not None:
        stmt = stmt.where(Question.job_id == job_id)
    if job_name and job_name.strip():
        stmt = stmt.where(Job.job_name.contains(job_name.strip()))
    if difficulty and difficulty.strip():
        stmt = stmt.where(Question.difficulty == difficulty.strip())
    if category and category.strip():
        stmt = stmt.where(Question.category == category.strip())
    stmt = stmt.order_by(Question.id.desc()).limit(2000)
    result = await db.execute(stmt)
    out = []
    for q, j in result.all():
        out.append(
            {
                "id": q.id,
                "question": q.content,
                "answer": q.answer,
                "difficulty": q.difficulty,
                "exam_points": q.exam_points,
                "category": q.category,
                "job": j.job_name,
                "job_id": j.id,
                "source_file_id": q.source_file_id,
            }
        )
    return success_response(message="ok", data={"questions": out, "total": len(out)})


@router.get("/query", summary="知识库查询（RAG）")
async def query_knowledge_api(
    keyword: str,
    chunk_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if not (keyword or "").strip():
        raise HTTPException(status_code=400, detail="keyword 不能为空")

    rag_result = await retrieve_context(
        db=db,
        query=keyword.strip(),
        filter_data={"chunk_type": chunk_type} if chunk_type else None,
    )
    chunks = rag_result.get("chunks", [])
    chunk_ids = [c.get("chunk_id") for c in chunks if c.get("chunk_id")]
    if not chunk_ids:
        return success_response(message="ok", data={"items": [], "total": 0})

    stmt = (
        select(Document, DocumentChunk, Job)
        .select_from(DocumentChunk)
        .join(Document, DocumentChunk.doc_id == Document.id, isouter=True)
        .join(Job, DocumentChunk.job_id == Job.id, isouter=True)
        .where(DocumentChunk.chunk_id.in_(chunk_ids))
    )
    rows = (await db.execute(stmt)).all()
    by_chunk = {}
    for doc, dc, job in rows:
        by_chunk[dc.chunk_id] = {
            "chunk_id": dc.chunk_id,
            "chunk_type": dc.chunk_type,
            "content": dc.content,
            "source_file": (doc.filename if doc else ""),
            "job_id": dc.job_id,
            "job_name": (job.job_name if job else ""),
        }
    ordered = [by_chunk[cid] for cid in chunk_ids if cid in by_chunk]
    return success_response(message="ok", data={"items": ordered, "total": len(ordered)})
