"""
Plan 1: RAG 核心能力增强工具集
覆盖：多格式解析 -> 清洗 -> 父子分块 -> 分类过滤 -> 去重 -> MySQL/Chroma 入库 -> 检索
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.env_util import env_int, env_str
from config.llm_conf import MODEL_KNOWLEDGE_GRAPH, call_llm
from models.rag_schema import Document, DocumentChunk
from services.kb.chroma_child import query_children

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except Exception:
    RecursiveCharacterTextSplitter = None

RAG_COLLECTION_NAME = env_str("RAG_COLLECTION_NAME", "interview_rag")
EMBED_MODEL_NAME = env_str("RAG_EMBED_MODEL_NAME", "text-embedding-3-small")
RERANK_TOP_K = env_int("RAG_RERANK_TOP_N", 3)
RAG_TOP_K = env_int("RAG_TOP_K", 5)
RAG_RETRIEVE_CACHE_TTL = env_int("RAG_RETRIEVE_CACHE_TTL", 60)
_embedding_cache: Dict[str, List[float]] = {}
_retrieve_cache: Dict[str, Dict[str, Any]] = {}

_PAGE_NUM_RE = re.compile(
    r"(?:^|\n)\s*(?:第\s*\d+\s*页|Page\s*\d+|-\s*\d+\s*-)\s*(?=\n|$)",
    re.IGNORECASE,
)
_HEADER_FOOTER_RE = re.compile(
    r"(?:版权|copyright|www\.|http[s]?://|保留所有权利|未经授权不得转载).*$",
    re.IGNORECASE | re.MULTILINE,
)
_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\ufeff\u2060]+")
_SPECIAL_RE = re.compile(r"[~`^*_]{3,}")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_PLACEHOLDER_RE = re.compile(r"^(?:N/?A|暂无|无|--+|待补充)$", re.IGNORECASE)


@dataclass
class RetrieveFilter:
    chunk_type: Optional[str] = None
    job_id: Optional[str] = None


def extract_text(file_path: str) -> str:
    """
    多格式统一抽取入口。失败时返回空字符串，不抛崩溃到上层。
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"文件路径不存在: {file_path}")
    if not p.is_file():
        raise ValueError(f"路径不是文件: {file_path}")

    ext = p.suffix.lower()
    try:
        if ext == ".pdf":
            return _extract_pdf(p)
        if ext in (".docx", ".doc"):
            return _extract_docx(p)
        if ext in (".txt", ".md"):
            return _extract_text_file(p)
        if ext in (".xlsx", ".xls"):
            return _extract_excel(p)
        if ext == ".csv":
            return _extract_csv(p)
        if ext == ".pptx":
            return _extract_pptx(p)
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            return _extract_ocr(p)
        raise ValueError(f"不支持的文件格式: {ext}")
    except (ValueError, FileNotFoundError):
        raise
    except Exception:
        return ""


def basic_clean(text: str) -> str:
    """
    基础清洗：
    - 去页码、页眉页脚
    - 去不可见字符与连续噪声符号
    - 合并多空行/空格
    """
    s = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    s = _PAGE_NUM_RE.sub("\n", s)
    s = _HEADER_FOOTER_RE.sub("", s)
    s = _INVISIBLE_RE.sub("", s)
    s = _SPECIAL_RE.sub(" ", s)
    s = _MULTI_SPACE_RE.sub(" ", s)
    s = _MULTI_NEWLINE_RE.sub("\n\n", s)
    return s.strip()


def deep_clean(text: str) -> str:
    """
    深度清洗：
    - 去重段落与无意义占位符
    - 标点与缩进归一化
    - 修复断句（行级拼接）
    """
    s = basic_clean(text)
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    dedup: List[str] = []
    seen: set[str] = set()
    for ln in lines:
        normalized = ln.replace("，", ",").replace("。", ".")
        if _PLACEHOLDER_RE.match(ln):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        dedup.append(ln)

    merged: List[str] = []
    buf = ""
    for ln in dedup:
        if not buf:
            buf = ln
            continue
        if buf.endswith(("。", "！", "？", ".", "!", "?", "；", ";", ":")):
            merged.append(buf)
            buf = ln
        else:
            # 行尾不是完整句时拼接，修复排版断裂
            buf = f"{buf} {ln}"
    if buf:
        merged.append(buf)

    out = "\n".join(merged)
    out = out.replace("，", "，").replace(",", "，")
    out = _MULTI_SPACE_RE.sub(" ", out)
    out = _MULTI_NEWLINE_RE.sub("\n\n", out)
    return out.strip()


def split_parent_child(text: str) -> List[Dict[str, Any]]:
    """
    父子分块：
    - parent: 2000/200
    - child: 500/50
    """
    clean_text = deep_clean(text)
    if not clean_text:
        return []
    if RecursiveCharacterTextSplitter is None:
        return _fallback_split_parent_child(clean_text)

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
    )

    parent_chunks = parent_splitter.split_text(clean_text)
    result: List[Dict[str, Any]] = []
    for parent_content in parent_chunks:
        parent_id = str(uuid.uuid4())
        result.append(
            {
                "chunk_id": parent_id,
                "content": parent_content,
                "chunk_level": "parent",
                "parent_id": None,
            }
        )
        for child_content in child_splitter.split_text(parent_content):
            result.append(
                {
                    "chunk_id": str(uuid.uuid4()),
                    "content": child_content,
                    "chunk_level": "child",
                    "parent_id": parent_id,
                }
            )
    return result


def classify_chunk(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    分块分类与价值过滤：
    - chunk_type: job/question/resume/other
    - 保留 conf >= 0.8
    - 丢弃 other 且 conf >= 0.9
    """
    classified = _classify_chunks_by_rule(chunks)

    try:
        llm_result = _classify_chunks_by_llm(chunks)
        if llm_result:
            classified = llm_result
    except Exception:
        pass

    filtered: List[Dict[str, Any]] = []
    for c in classified:
        ctype = c.get("chunk_type", "other")
        conf = float(c.get("confidence", 0.0))
        if ctype == "other" and conf >= 0.9:
            continue
        if conf >= 0.8:
            filtered.append(c)
    return filtered


async def classify_chunk_llm(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    异步 LLM 分类与价值过滤：稳定输出 job/question/resume/other。
    """
    if not chunks:
        return []
    sample_payload = []
    for c in chunks[:80]:
        sample_payload.append(
            {
                "chunk_id": c.get("chunk_id"),
                "content": (c.get("content") or "")[:700],
            }
        )
    prompt = (
        "你是RAG分块分类器。请对每个chunk输出：chunk_id、chunk_type(job/question/resume/other)、"
        "confidence(0-1)、value_score(0-1)。\n"
        "严格只返回JSON数组，不要markdown。\n"
        f"输入={sample_payload}"
    )
    try:
        raw = await call_llm(
            prompt=prompt,
            system_prompt="仅输出JSON数组。",
            model=MODEL_KNOWLEDGE_GRAPH,
        )
        import json

        clean_raw = raw.strip()
        if clean_raw.startswith("```"):
            clean_raw = clean_raw.replace("```json", "").replace("```", "").strip()
        rows = json.loads(clean_raw)
        mapping = {str(r.get("chunk_id")): r for r in rows if isinstance(r, dict)}
        out: List[Dict[str, Any]] = []
        for c in chunks:
            row = mapping.get(str(c.get("chunk_id")), {})
            chunk_type = row.get("chunk_type", "other")
            if chunk_type not in {"job", "question", "resume", "other"}:
                chunk_type = "other"
            conf = float(row.get("confidence", 0.0))
            value_score = float(row.get("value_score", 0.0))
            item = {
                **c,
                "chunk_type": chunk_type,
                "confidence": conf,
                "value_score": value_score,
            }
            if chunk_type == "other" and conf >= 0.9:
                continue
            if conf >= 0.8 and value_score >= 0.7:
                out.append(item)
        return out or classify_chunk(chunks)
    except Exception:
        return classify_chunk(chunks)


async def dedup_chunk(
    chunks: List[Dict[str, Any]],
    db: Optional[AsyncSession] = None,
) -> List[Dict[str, Any]]:
    """
    基于 SHA256 去重：
    - 内存内去重
    - 可选查询 MySQL(document_chunks.content_hash) 去重
    """
    memory_seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    db_hashes: set[str] = set()
    if db is not None:
        stmt: Select[Any] = select(DocumentChunk.content_hash)
        res = await db.execute(stmt)
        db_hashes = {row[0] for row in res.fetchall() if row and row[0]}

    for chunk in chunks:
        content = (chunk.get("content") or "").strip()
        if not content:
            continue
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if content_hash in memory_seen:
            continue
        if content_hash in db_hashes:
            continue
        memory_seen.add(content_hash)
        chunk["content_hash"] = content_hash
        out.append(chunk)
    return out


async def save_to_mysql(
    chunks: List[Dict[str, Any]],
    file_info: Dict[str, Any],
    db: AsyncSession,
) -> int:
    """
    写入 documents + document_chunks，返回 doc_id。
    """
    document = Document(
        filename=file_info.get("filename", ""),
        file_type=file_info.get("file_type", ""),
        status=file_info.get("status", "active"),
    )
    db.add(document)
    await db.flush()

    for c in chunks:
        row = DocumentChunk(
            doc_id=document.id,
            chunk_id=c["chunk_id"],
            content=c["content"],
            chunk_level=c["chunk_level"],
            parent_id=c.get("parent_id"),
            chunk_type=c.get("chunk_type", "other"),
            job_id=c.get("job_id"),
            content_hash=c.get("content_hash"),
        )
        db.add(row)
    await db.commit()
    return document.id


def init_chroma_collection() -> Any:
    client = chromadb.PersistentClient(path=env_str("CHROMA_DB_PATH", "./chroma_db"))
    return client.get_or_create_collection(
        name=RAG_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def embed_chunk(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    仅对子块做向量化，输出 embedding/vector_id 字段。
    """
    from config import rag_conf

    embed_model = rag_conf.embedding_model
    if embed_model is None:
        return []

    child_chunks = [c for c in chunks if c.get("chunk_level") == "child"]
    if not child_chunks:
        return []
    uncached_texts: List[str] = []
    uncached_indices: List[int] = []
    for idx, c in enumerate(child_chunks):
        text = c["content"]
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key in _embedding_cache:
            c["embedding"] = _embedding_cache[key]
        else:
            uncached_indices.append(idx)
            uncached_texts.append(text)
            c["_cache_key"] = key
    if uncached_texts:
        vectors = embed_model.encode(uncached_texts).tolist()
        for i, emb in zip(uncached_indices, vectors):
            c = child_chunks[i]
            key = c.pop("_cache_key")
            _embedding_cache[key] = emb
            c["embedding"] = emb

    for c in child_chunks:
        c["vector_id"] = str(uuid.uuid4())
        c["embedding_model"] = EMBED_MODEL_NAME
    return child_chunks


def save_to_chroma(chunks: List[Dict[str, Any]]) -> None:
    """
    仅写入子块向量。元数据保留 vector_id/chunk_id/chunk_type/job_id。
    """
    col = init_chroma_collection()
    child_chunks = [c for c in chunks if c.get("chunk_level") == "child" and c.get("embedding")]
    if not child_chunks:
        return

    ids = [c["vector_id"] for c in child_chunks]
    embeddings = [c["embedding"] for c in child_chunks]
    documents = [c["content"] for c in child_chunks]
    metadatas = [
        {
            "vector_id": c["vector_id"],
            "chunk_id": c["chunk_id"],
            "chunk_type": c.get("chunk_type", "other"),
            "job_id": str(c.get("job_id", "")),
        }
        for c in child_chunks
    ]
    col.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


async def run_full_pipeline(
    file_path: str,
    file_info: Dict[str, Any],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    全流程：上传文件路径 -> 解析 -> 清洗 -> 分块 -> 分类 -> 去重 -> MySQL -> Chroma
    """
    raw = extract_text(file_path)
    cleaned = deep_clean(raw)
    chunks = split_parent_child(cleaned)
    chunks = await classify_chunk_llm(chunks)
    job_id = file_info.get("job_id")
    if job_id is not None:
        for c in chunks:
            c["job_id"] = job_id
    chunks = await dedup_chunk(chunks, db=db)
    doc_id = await save_to_mysql(chunks, file_info=file_info, db=db)
    embedded = embed_chunk(chunks)
    save_to_chroma(embedded)
    return {
        "doc_id": doc_id,
        "total_chunks": len(chunks),
        "embedded_chunks": len(embedded),
        "filename": file_info.get("filename", ""),
    }


async def retrieve_context(
    db: AsyncSession,
    query: str,
    filter_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    检索流程：
    query preprocess -> Chroma 检索 top10 -> metadata 过滤 -> rerank top5 -> 回表父块 -> 拼接上下文
    """
    start = time.perf_counter()
    cache_key = f"{(query or '').strip()}|{(filter_data or {}).get('chunk_type','')}|{(filter_data or {}).get('job_id','')}"
    now_ts = time.time()
    cached = _retrieve_cache.get(cache_key)
    if cached and now_ts - float(cached.get("ts", 0)) <= RAG_RETRIEVE_CACHE_TTL:
        return cached["value"]
    f = RetrieveFilter(
        chunk_type=(filter_data or {}).get("chunk_type"),
        job_id=(filter_data or {}).get("job_id"),
    )
    q = await _preprocess_query_llm(query)
    rewritten = await _rewrite_query_llm(q)
    merged_queries = [q, *rewritten]
    seen_q: set[str] = set()
    queries: List[str] = []
    for qx in merged_queries:
        k = (qx or "").strip()
        if not k or k in seen_q:
            continue
        seen_q.add(k)
        queries.append(k)

    vector_hits: List[Dict[str, Any]] = []
    for qx in queries[:4]:
        vector_hits.extend(query_children(qx, top_k=RAG_TOP_K))

    candidate_items: List[Dict[str, Any]] = []
    chunk_ids: List[str] = []
    for hit in vector_hits:
        meta = hit.get("metadata") or {}
        if f.chunk_type and meta.get("chunk_type") != f.chunk_type:
            continue
        if f.job_id and str(meta.get("job_id") or "") != str(f.job_id):
            continue
        cid = str(meta.get("chunk_id") or "")
        if not cid:
            continue
        chunk_ids.append(cid)
        candidate_items.append(
            {
                "chunk_id": cid,
                "content": hit.get("document", ""),
                "score": 1 - float(hit.get("distance") or 1.0),
                "chunk_type": meta.get("chunk_type", "other"),
                "job_id": meta.get("job_id"),
            }
        )

    # 多query检索后去重：同 chunk_id 仅保留最高初始分
    dedup_map: Dict[str, Dict[str, Any]] = {}
    for item in candidate_items:
        cid = item["chunk_id"]
        prev = dedup_map.get(cid)
        if (prev is None) or float(item.get("score", 0.0)) > float(prev.get("score", 0.0)):
            dedup_map[cid] = item
    candidate_items = list(dedup_map.values())

    if not candidate_items:
        elapsed = time.perf_counter() - start
        result = {"context": "", "chunks": [], "retrieve_time": round(elapsed, 4)}
        _retrieve_cache[cache_key] = {"ts": now_ts, "value": result}
        return result

    reranked = _rerank_items(q, candidate_items)[:RERANK_TOP_K]
    reranked = [x for x in reranked if float(x.get("rerank_score", 0.0)) >= 0.2]
    id_set = {item["chunk_id"] for item in reranked}

    stmt = select(DocumentChunk).where(DocumentChunk.chunk_id.in_(list(id_set)))
    res = await db.execute(stmt)
    child_rows = {row.chunk_id: row for row in res.scalars().all()}
    parent_id_set = {row.parent_id for row in child_rows.values() if row and row.parent_id}
    parents = {}
    if parent_id_set:
        p_stmt = select(DocumentChunk).where(DocumentChunk.chunk_id.in_(list(parent_id_set)))
        p_res = await db.execute(p_stmt)
        parents = {row.chunk_id: row for row in p_res.scalars().all()}

    context_parts: List[str] = []
    chunks_out: List[Dict[str, Any]] = []
    for item in reranked:
        row = child_rows.get(item["chunk_id"])
        if not row:
            continue
        parent = parents.get(row.parent_id) if row.parent_id else None
        parent_text = parent.content if parent else ""
        child_text = row.content
        assembled = f"[父块]\n{parent_text}\n[子块]\n{child_text}".strip()
        context_parts.append(assembled)
        chunks_out.append(
            {
                "chunk_id": row.chunk_id,
                "chunk_type": row.chunk_type,
                "content": row.content,
                "parent_id": row.parent_id,
                "score": item.get("rerank_score", item["score"]),
            }
        )

    context = "\n\n".join(context_parts)
    if len(context) > 3000:
        context = context[:3000]

    elapsed = time.perf_counter() - start
    result = {"context": context, "chunks": chunks_out, "retrieve_time": round(elapsed, 4)}
    _retrieve_cache[cache_key] = {"ts": now_ts, "value": result}
    return result


def _extract_pdf(path: Path) -> str:
    import pdfplumber
    from PyPDF2 import PdfReader

    parts: List[str] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                txt = page.extract_text() or ""
                if txt.strip():
                    parts.append(f"[第{page_no}页]\n{txt.strip()}")
        if parts:
            return "\n\n".join(parts)
    except Exception:
        pass

    reader = PdfReader(str(path))
    for idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        if txt.strip():
            parts.append(f"[第{idx}页]\n{txt.strip()}")
    return "\n\n".join(parts)


def _extract_docx(path: Path) -> str:
    from docx import Document as DocxDocument

    doc = DocxDocument(str(path))
    paras = [p.text.strip() for p in doc.paragraphs if (p.text or "").strip()]
    return "\n\n".join(paras)


def _extract_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_excel(path: Path) -> str:
    import pandas as pd

    lines: List[str] = []
    all_sheets = pd.read_excel(path, sheet_name=None)
    for sheet_name, df in all_sheets.items():
        for i, row in df.fillna("").iterrows():
            cols = [f"{col}: {str(val).strip()}" for col, val in row.items() if str(val).strip()]
            if cols:
                lines.append(f"工作表={sheet_name} | 行={i + 1} | " + " | ".join(cols))
    return "\n".join(lines)


def _extract_csv(path: Path) -> str:
    lines: List[str] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            cols = [f"{k}: {str(v).strip()}" for k, v in row.items() if k and str(v).strip()]
            if cols:
                lines.append(f"工作表=csv | 行={i} | " + " | ".join(cols))
    return "\n".join(lines)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    prs = Presentation(str(path))
    pages: List[str] = []
    for idx, slide in enumerate(prs.slides, start=1):
        t_list: List[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text") and str(shape.text).strip():
                t_list.append(str(shape.text).strip())
        notes = ""
        if slide.has_notes_slide:
            notes = (slide.notes_slide.notes_text_frame.text or "").strip()
        page_text = "\n".join(t_list)
        pages.append(f"[第{idx}页]\n{page_text}\n[备注]\n{notes}".strip())
    return "\n\n".join(pages)


def _extract_ocr(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""
    try:
        img = Image.open(str(path))
        return pytesseract.image_to_string(img, lang="chi_sim+eng")
    except Exception:
        return ""


def _fallback_split_parent_child(text: str) -> List[Dict[str, Any]]:
    parents = [text[i : i + 2000] for i in range(0, len(text), 1800)]
    out: List[Dict[str, Any]] = []
    for p in parents:
        pid = str(uuid.uuid4())
        out.append({"chunk_id": pid, "content": p, "chunk_level": "parent", "parent_id": None})
        for i in range(0, len(p), 450):
            child = p[i : i + 500]
            if child.strip():
                out.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "content": child,
                        "chunk_level": "child",
                        "parent_id": pid,
                    }
                )
    return out


def _classify_chunks_by_rule(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for c in chunks:
        content = (c.get("content") or "").lower()
        ctype = "other"
        conf = 0.75
        if any(k in content for k in ("岗位", "职责", "任职要求", "技术栈", "job")):
            ctype = "job"
            conf = 0.86
        elif any(k in content for k in ("题目", "问题", "question", "选择题", "简答题")):
            ctype = "question"
            conf = 0.88
        elif any(k in content for k in ("简历", "项目经历", "工作经历", "教育经历", "自我评价")):
            ctype = "resume"
            conf = 0.87
        out.append({**c, "chunk_type": ctype, "confidence": conf})
    return out


def _classify_chunks_by_llm(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chunks:
        return []
    sample_payload = []
    for c in chunks[:20]:
        sample_payload.append(
            {
                "chunk_id": c.get("chunk_id"),
                "content": (c.get("content") or "")[:600],
            }
        )
    prompt = (
        "请把每个分块分类为 job/question/resume/other，并给出 0-1 置信度。"
        "只返回 JSON 数组，元素字段为 chunk_id, chunk_type, confidence。\n"
        f"输入: {sample_payload}"
    )

    async def _invoke() -> str:
        return await call_llm(
            prompt=prompt,
            system_prompt="你是分类器，只输出 JSON。",
            model=MODEL_KNOWLEDGE_GRAPH,
        )

    try:
        raw = asyncio.run(_invoke())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        raw = loop.run_until_complete(_invoke())
    import json

    rows = json.loads(raw)
    mapping = {str(r.get("chunk_id")): r for r in rows if isinstance(r, dict)}
    out = []
    for c in chunks:
        row = mapping.get(str(c.get("chunk_id")))
        if not row:
            out.append({**c, "chunk_type": "other", "confidence": 0.7})
            continue
        out.append(
            {
                **c,
                "chunk_type": row.get("chunk_type", "other"),
                "confidence": float(row.get("confidence", 0.7)),
            }
        )
    return out


def _preprocess_query(query: str) -> str:
    q = (query or "").strip()
    q = re.sub(r"\s+", " ", q)
    replacements = {"Pyhton": "Python", "javscript": "javascript", "面視": "面试"}
    for wrong, right in replacements.items():
        q = q.replace(wrong, right)
    if len(q) < 3:
        q = f"{q} 面试"
    return q


async def _preprocess_query_llm(query: str) -> str:
    base = _preprocess_query(query)
    prompt = (
        "请对用户检索问题做：纠错、语义润色、意图识别后的规范化表达。"
        "要求保留原意，不扩写无关信息。"
        '只输出一个字符串，JSON格式：{"query":"..."}。\n'
        f"输入={base}"
    )
    try:
        raw = await call_llm(
            prompt=prompt,
            system_prompt="你是检索查询优化器，只输出JSON。",
            model=MODEL_KNOWLEDGE_GRAPH,
        )
        import json

        s = raw.strip().replace("```json", "").replace("```", "").strip()
        obj = json.loads(s)
        q = (obj.get("query") or "").strip()
        return q or base
    except Exception:
        return base


async def _rewrite_query_llm(query: str) -> List[str]:
    prompt = (
        "请把检索问题改写为3条语义等价但表述不同的查询，用于增强召回。"
        "不得偏离原问题。只输出JSON：{\"queries\":[\"...\",\"...\",\"...\"]}\n"
        f"输入={query}"
    )
    try:
        raw = await call_llm(
            prompt=prompt,
            system_prompt="你是查询改写器，只输出JSON。",
            model=MODEL_KNOWLEDGE_GRAPH,
        )
        import json

        s = raw.strip().replace("```json", "").replace("```", "").strip()
        arr = json.loads(s).get("queries") or []
        out = [(x or "").strip() for x in arr if (x or "").strip()]
        return out[:3]
    except Exception:
        return []


def _rerank_items(query: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        from FlagEmbedding import FlagReranker  # type: ignore

        model_name = env_str("RAG_RERANK_MODEL", "BAAI/bge-reranker-base")
        reranker = FlagReranker(model_name, use_fp16=False)
        pairs = [[query, i.get("content", "")] for i in items]
        scores = reranker.compute_score(pairs)
        for i, s in zip(items, scores):
            i["rerank_score"] = float(s)
        return sorted(items, key=lambda x: x.get("rerank_score", 0), reverse=True)
    except Exception:
        q_tokens = [t for t in re.split(r"[\s,，。；;]+", query.lower()) if t]
        for item in items:
            content = (item.get("content") or "").lower()
            c = Counter()
            for t in q_tokens:
                c[t] = content.count(t)
            item["rerank_score"] = float(sum(c.values()))
        return sorted(items, key=lambda x: x.get("rerank_score", 0), reverse=True)
