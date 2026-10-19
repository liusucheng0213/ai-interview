"""
上传后流水线：解析 → 结构化入库（MySQL）→ 父子块落库 → 子块向量化（Chroma）。
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.rag_schema import Job, Question, KnowledgeFile, KbParentChunk, KbChildChunk
from services.kb.chunking import build_plans
from services.kb.chroma_child import add_child_embeddings, delete_children_by_file_id
from services.kb.excel_questions import extract_structured_from_excel_rows
from services.kb.file_extract import extract_from_bytes, sanitize_extracted_text
from services.kb.llm_structure import structured_extract

logger = logging.getLogger(__name__)
_PURE_NUM_RE = re.compile(r"^[\[\(（【]?\s*\d+(?:\.\d+)?\s*[\]\)）】]?$")
_OPTION_RE = re.compile(r"^[A-Fa-f](?:\s*[,，/、\s]\s*[A-Fa-f])*$")
_GARBAGE_RE = re.compile(
    r"(?:https?://|www\.|分类\s*[:：]|标签\s*[:：]|点击|扫码|关注公众号|免责声明|版权所有)",
    re.IGNORECASE,
)
_MEANINGLESS_LINE_RE = re.compile(r"^[\W_]+$", re.UNICODE)


def _normalize_answer(v: Any) -> str:
    s = sanitize_extracted_text(v)[:1000]
    if not s:
        return "未标注答案"
    if _PURE_NUM_RE.fullmatch(s):
        return "未标注答案"
    s_upper = s.upper().replace("，", ",").replace("、", ",").replace("/", ",")
    s_upper = re.sub(r"\s+", "", s_upper)
    if _OPTION_RE.fullmatch(s_upper):
        parts = [x for x in s_upper.split(",") if x]
        dedup: List[str] = []
        for p in parts:
            if p not in dedup:
                dedup.append(p)
        return ",".join(dedup) if dedup else "未标注答案"
    if s in ("√", "×", "对", "错", "正确", "错误"):
        return s
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return "未标注答案"
    return s


def _looks_like_garbage_text(text: str) -> bool:
    s = sanitize_extracted_text(text or "")
    if not s:
        return True
    if len(s) < 6:
        return True
    if _MEANINGLESS_LINE_RE.fullmatch(s):
        return True
    if _GARBAGE_RE.search(s):
        return True
    return False


def _is_valid_question_item(q: dict) -> bool:
    content = sanitize_extracted_text(q.get("content") or "")[:1200]
    if _looks_like_garbage_text(content):
        return False
    answer = _normalize_answer(q.get("answer"))
    # 若题目极长但答案完全缺失，通常是抽取失败的整段噪音，直接丢弃。
    if len(content) > 220 and answer == "未标注答案":
        return False
    return True


def _validate_structured_quality(data: Dict[str, List[dict]]) -> tuple[bool, str]:
    jobs = data.get("jobs") or []
    questions = data.get("questions") or []
    if not jobs and not questions:
        return False, "结构化提取为空，已中止入库（避免写入垃圾信息）"
    if not questions:
        return False, "未提取到有效题目，已中止入库（避免写入垃圾信息）"
    return True, "ok"


def _merge_structured(
    llm_data: Dict[str, Any],
    excel_data: Dict[str, Any],
    filename: str,
) -> Dict[str, List[dict]]:
    """
    统一结构化结果来源，保证 question 与向量块使用同一份干净文本。
    """
    merged_jobs: Dict[str, dict] = {}
    merged_questions: List[dict] = []
    seen_q: set[tuple[str, str, str]] = set()

    def upsert_job(j: dict):
        name = sanitize_extracted_text(j.get("job_name"))[:128]
        if not name:
            return
        tech = j.get("tech_stack") or []
        if isinstance(tech, str):
            tech = [x.strip() for x in tech.replace("，", ",").split(",") if x.strip()]
        tech = [sanitize_extracted_text(x)[:64] for x in tech if sanitize_extracted_text(x)]
        desc = sanitize_extracted_text(j.get("description"))[:2000]
        if not desc:
            desc = f"{name}岗位，来源文档《{filename}》，核心关注{('、'.join(tech[:6]) if tech else '基础能力与项目实践')}。"
        if name not in merged_jobs:
            merged_jobs[name] = {"job_name": name, "tech_stack": tech[:20], "description": desc}
        else:
            existed = set(merged_jobs[name]["tech_stack"])
            for t in tech:
                if t not in existed:
                    merged_jobs[name]["tech_stack"].append(t)
            if desc and not merged_jobs[name].get("description"):
                merged_jobs[name]["description"] = desc

    def append_question(q: dict):
        content = sanitize_extracted_text(q.get("content"))[:1200]
        if not content:
            return
        job_name = sanitize_extracted_text(q.get("job_name"))[:128]
        if not job_name:
            job_name = next(iter(merged_jobs.keys()), "")
        if not job_name:
            return
        if job_name not in merged_jobs:
            upsert_job({"job_name": job_name, "tech_stack": [], "description": ""})
        answer = _normalize_answer(q.get("answer"))
        dedupe_key = (job_name, content, answer)
        if dedupe_key in seen_q:
            return
        seen_q.add(dedupe_key)
        exam_points = sanitize_extracted_text(q.get("exam_points"))[:500]
        if not exam_points:
            exam_points = "综合知识;公共基础"
        merged_questions.append(
            {
                "job_name": job_name,
                "content": content,
                "answer": answer,
                "difficulty": sanitize_extracted_text(q.get("difficulty"))[:32] or "medium",
                "exam_points": exam_points,
                "category": sanitize_extracted_text(q.get("category"))[:64] or "未分类",
                "source_row": q.get("source_row"),
            }
        )

    for j in (llm_data.get("jobs") or []):
        if isinstance(j, dict):
            upsert_job(j)
    for j in (excel_data.get("jobs") or []):
        if isinstance(j, dict):
            upsert_job(j)

    for q in (excel_data.get("questions") or []):
        if isinstance(q, dict):
            append_question(q)
    for q in (llm_data.get("questions") or []):
        if isinstance(q, dict):
            append_question(q)

    filtered_questions = [q for q in merged_questions if _is_valid_question_item(q)]
    related_job_names = {q.get("job_name") for q in filtered_questions if q.get("job_name")}
    filtered_jobs = [j for j in merged_jobs.values() if j.get("job_name") in related_job_names]
    return {"jobs": filtered_jobs, "questions": filtered_questions}


def _build_structured_text(data: Dict[str, List[dict]]) -> str:
    lines: List[str] = []
    for j in data.get("jobs") or []:
        lines.append(f"岗位: {j.get('job_name', '')}")
        lines.append(f"技术栈: {';'.join(j.get('tech_stack') or [])}")
        lines.append(f"岗位描述: {j.get('description') or ''}")
    for q in data.get("questions") or []:
        lines.append(f"岗位: {q.get('job_name', '')}")
        lines.append(f"题目: {q.get('content', '')}")
        lines.append(f"答案: {q.get('answer', '')}")
        lines.append(f"考点: {q.get('exam_points', '')}")
        lines.append(f"难度: {q.get('difficulty', '')}")
        lines.append(f"题型: {q.get('category', '')}")
    return sanitize_extracted_text("\n".join(lines))


async def _set_status(db: AsyncSession, file_id: int, status: str, msg: Optional[str] = None):
    await db.execute(
        update(KnowledgeFile)
        .where(KnowledgeFile.id == file_id)
        .values(parse_status=status, parse_message=(msg or "")[:2000])
    )
    await db.commit()


async def run_ingest_for_file(db: AsyncSession, file_id: int) -> None:
    """后台任务入口：根据 knowledge_file.id 处理入库与向量。"""
    res = await db.execute(select(KnowledgeFile).where(KnowledgeFile.id == file_id))
    kf = res.scalar_one_or_none()
    if not kf:
        logger.warning(f"[RAG v2] knowledge_file {file_id} 不存在")
        return

    path = Path(kf.storage_path)
    if not path.is_absolute():
        path = Path(".") / path
    if not path.exists():
        alt = Path("./storage") / kf.storage_path
        if alt.exists():
            path = alt
    if not path.exists():
        await _set_status(db, file_id, "error", "本地文件不存在")
        return

    try:
        await _set_status(db, file_id, "parsing")
        file_bytes = path.read_bytes()
        ex = extract_from_bytes(file_bytes, kf.original_filename)
        clean_text = sanitize_extracted_text(ex.full_text or "")

        await db.execute(
            update(KnowledgeFile)
            .where(KnowledgeFile.id == file_id)
            .values(char_count=len(clean_text or ""))
        )
        await db.commit()

        await _set_status(db, file_id, "structuring")
        llm_data = await structured_extract(clean_text)
        excel_data = extract_structured_from_excel_rows(ex.excel_rows or []) if ex.excel_rows else {"jobs": [], "questions": []}
        data = _merge_structured(llm_data, excel_data, kf.original_filename)
        is_ok, quality_msg = _validate_structured_quality(data)
        if not is_ok:
            await _set_status(db, file_id, "error", quality_msg)
            logger.warning("[RAG v2] 结构化质量不达标 file_id=%s reason=%s", file_id, quality_msg)
            return
        structured_jobs = len(data.get("jobs") or [])
        structured_questions = len(data.get("questions") or [])
        filled_exam_points = 0
        # 同一文件重入库前清理旧结构化题目，避免重复与脏数据累积。
        await db.execute(delete(Question).where(Question.source_file_id == file_id))
        await db.commit()

        job_name_to_id: dict[str, int] = {}
        r0 = await db.execute(select(Job))
        for j0 in r0.scalars().all():
            job_name_to_id[j0.job_name] = j0.id

        src_exists_res = await db.execute(select(KnowledgeFile.id).where(KnowledgeFile.id == file_id))
        source_file_ref = file_id if src_exists_res.scalar_one_or_none() else None

        for j in data.get("jobs") or []:
            name = (j.get("job_name") or "").strip()
            if not name:
                continue
            ts = j.get("tech_stack")
            if isinstance(ts, list):
                tech = [sanitize_extracted_text(x) for x in ts if sanitize_extracted_text(x)]
            elif isinstance(ts, str) and ts.strip():
                tech = [x.strip() for x in ts.replace("，", ",").split(",") if x.strip()]
            else:
                tech = []
            desc = sanitize_extracted_text(j.get("description"))[:2000]
            if not desc:
                desc = f"{name}岗位，核心关注{('、'.join(tech[:6]) if tech else '基础能力与项目实践')}。"
            if name in job_name_to_id:
                jid = job_name_to_id[name]
                exj = await db.get(Job, jid)
                if exj:
                    if tech and not exj.tech_stack:
                        exj.tech_stack = tech
                    elif tech and exj.tech_stack:
                        existed = set(exj.tech_stack or [])
                        exj.tech_stack = list(existed.union(set(tech)))
                    if desc:
                        exj.description = desc
                    exj.source_file_id = source_file_ref
            else:
                job = Job(
                    job_name=name[:128],
                    tech_stack=tech or None,
                    description=desc,
                    source_file_id=source_file_ref,
                )
                db.add(job)
                await db.flush()
                job_name_to_id[name] = job.id
        await db.commit()

        for q in data.get("questions") or []:
            jn = (q.get("job_name") or "").strip()
            jid = job_name_to_id.get(jn)
            if jid is None and job_name_to_id:
                jid = next(iter(job_name_to_id.values()))
            if jid is None:
                continue
            content = (q.get("content") or "").strip()
            if not content:
                continue
            exam_points = sanitize_extracted_text(q.get("exam_points"))[:500] or "综合知识;公共基础"
            if exam_points:
                filled_exam_points += 1
            db.add(
                Question(
                    job_id=jid,
                    content=content,
                    answer=_normalize_answer(q.get("answer")),
                    difficulty=(q.get("difficulty") or None),
                    exam_points=exam_points,
                    category=(q.get("category") or None),
                    source_file_id=source_file_ref,
                    source_row=q.get("source_row"),
                )
            )
        await db.commit()
        logger.info(
            "[RAG v2] 结构化入库 file_id=%s jobs=%s questions=%s exam_points_filled=%s",
            file_id,
            structured_jobs,
            structured_questions,
            filled_exam_points,
        )

        await _set_status(db, file_id, "chunking")
        structured_text = _build_structured_text(data)
        chunk_seed_text = sanitize_extracted_text(structured_text)
        plans = build_plans(ex.kind, chunk_seed_text, ex.excel_rows)
        if not plans and chunk_seed_text:
            plans = build_plans("txt", chunk_seed_text, None)

        delete_children_by_file_id(file_id)
        await db.execute(delete(KbChildChunk).where(KbChildChunk.knowledge_file_id == file_id))
        await db.execute(delete(KbParentChunk).where(KbParentChunk.knowledge_file_id == file_id))
        await db.commit()

        parent_count = 0
        child_count = 0
        embed_batch: list[dict] = []
        sort_order = 0

        for plan in plans:
            sort_order += 1
            valid_children: List[str] = []
            for ct in plan.child_texts:
                ct = (ct or "").strip()
                if len(ct) < 10:
                    continue
                valid_children.append(ct)
            # 避免“父块存在但子块为空”
            if not valid_children and plan.preview:
                valid_children = [plan.preview[:500]]
            if not valid_children:
                continue
            parent = KbParentChunk(
                knowledge_file_id=file_id,
                title=plan.title,
                sort_order=sort_order,
                source_kind=plan.source_kind,
                source_row=plan.source_row,
                preview=(plan.preview or "")[:1024] or None,
            )
            db.add(parent)
            await db.flush()
            parent_count += 1
            seq = 0
            for ct in valid_children:
                seq += 1
                child = KbChildChunk(
                    parent_id=parent.id,
                    knowledge_file_id=file_id,
                    seq=seq,
                    content=ct,
                    char_len=len(ct),
                )
                db.add(child)
                await db.flush()
                chroma_id = f"kbc-{child.id}"
                child.chroma_id = chroma_id
                embed_batch.append(
                    {
                        "chroma_id": chroma_id,
                        "content": ct,
                        "chunk_id": child.id,
                        "parent_id": parent.id,
                        "file_id": file_id,
                        "owner_user_id": kf.user_id,
                        "visibility": kf.visibility,
                        "org_id": kf.org_id or "",
                    }
                )
                child_count += 1

        await db.commit()

        await _set_status(db, file_id, "vectorizing")
        if embed_batch:
            add_child_embeddings(embed_batch)

        await db.execute(
            update(KnowledgeFile)
            .where(KnowledgeFile.id == file_id)
            .values(
                parse_status="done",
                parent_chunk_count=parent_count,
                child_chunk_count=child_count,
                parse_message="ok",
            )
        )
        await db.commit()
        logger.info(
            "[RAG v2] 文件处理完成 file_id=%s parent=%s child=%s jobs=%s questions=%s",
            file_id,
            parent_count,
            child_count,
            structured_jobs,
            structured_questions,
        )

    except Exception as e:
        logger.exception(f"[RAG v2] 入库失败 file_id={file_id}")
        # 先回滚，避免会话处于 PendingRollback 状态导致后续 _set_status 也失败。
        await db.rollback()
        await _set_status(db, file_id, "error", str(e)[:1500])
