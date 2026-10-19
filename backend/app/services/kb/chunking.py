"""
父子分块：Excel 按行父块、长字段子块；文档按标题父块；TXT 按大段父块。
子块长度约 300~500 字（字符），禁止跨行（Excel）/ 禁止把 AI 总结写入内容。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

CHILD_LOW = 300
CHILD_HIGH = 500
CHILD_MIN = 20


@dataclass
class ParentPlan:
    title: str
    source_kind: str
    source_row: Optional[int]
    child_texts: List[str] = field(default_factory=list)
    preview: str = ""


def split_into_child_chunks(text: str, low: int = CHILD_LOW, high: int = CHILD_HIGH) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= high:
        return [text] if len(text) >= CHILD_MIN else []
    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + high, n)
        if end < n:
            cut = max(i + low, end - 80)
            slice_ = text[i:end]
            for sep in ("。", "！", "？", ".", "\n", "；", ";"):
                p = slice_.rfind(sep, low - i if low > i else 0)
                if p != -1:
                    cut = i + p + 1
                    break
            if cut <= i:
                cut = end
        else:
            cut = end
        piece = text[i:cut].strip()
        if piece and len(piece) >= CHILD_MIN:
            chunks.append(piece)
        i = cut if cut > i else end
    if not chunks and len(text) >= 10:
        # 短文本兜底：避免后续父块无子块
        return [text[:high]]
    return chunks


def _normalize_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def plans_from_excel_rows(rows: List[dict[str, Any]]) -> List[ParentPlan]:
    """每行一个父块；长文本字段仅在行内切子块。"""
    plans: List[ParentPlan] = []
    title_keys = ("岗位", "职位", "题目", "题目标题", "名称", "标题", "方向", "类别")
    long_keys = ("答案", "解析", "参考", "技术栈", "描述", "考点", "要点", "内容", "备注")

    for idx, row in enumerate(rows, start=2):
        cells = {str(k).strip(): _normalize_cell(v) for k, v in row.items() if k}
        title_parts = [cells[k] for k in cells if any(t in k for t in title_keys) and cells[k]]
        if not title_parts:
            title_parts = [v for k, v in cells.items() if v and len(v) < 60][:3]
        title = " · ".join(title_parts) if title_parts else f"表格行 {idx}"
        long_blob_parts = [f"{k}: {cells[k]}" for k in cells if any(lk in k for lk in long_keys) and cells[k]]
        if not long_blob_parts:
            long_blob_parts = [f"{k}: {v}" for k, v in cells.items() if v and len(v) >= 80]
        if not long_blob_parts:
            long_blob_parts = [f"{k}: {v}" for k, v in cells.items() if v]
        blob = "\n".join(long_blob_parts)
        children = split_into_child_chunks(blob)
        if not children and blob:
            children = [blob]
        preview = (blob[:1000] + "…") if len(blob) > 1000 else blob
        plans.append(
            ParentPlan(
                title=title[:500],
                source_kind="excel_row",
                source_row=idx,
                child_texts=children,
                preview=preview,
            )
        )
    return plans


def plans_from_document_text(text: str, source_kind: str = "doc") -> List[ParentPlan]:
    """按一级/二级标题或编号行切父块，正文切子块。"""
    lines = text.replace("\r\n", "\n").split("\n")
    plans: List[ParentPlan] = []
    current_title = "文档开头"
    current_body: List[str] = []

    heading_re = re.compile(r"^\s*(#{1,3}\s+|[一二三四五六七八九十]+[、.．]|\d+[.．、]\s*|\[[^\]]+\])\s*(.+)?$")

    def flush():
        nonlocal current_title, current_body
        body = "\n".join(x.strip() for x in current_body if x.strip()).strip()
        if not body and current_title == "文档开头":
            return
        children = split_into_child_chunks(body) if body else []
        if not children and body:
            children = [body]
        preview = (body[:1000] + "…") if len(body) > 1000 else body
        plans.append(
            ParentPlan(
                title=current_title[:500],
                source_kind="doc_heading" if source_kind == "doc" else "pdf_heading",
                source_row=None,
                child_texts=children,
                preview=preview or current_title,
            )
        )
        current_body = []

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if len(s) < 80 and (heading_re.match(s) or (len(s) < 40 and not current_body)):
            flush()
            current_title = re.sub(r"^#{1,3}\s*", "", s).strip()[:500]
            continue
        current_body.append(s)
    flush()

    if not plans:
        children = split_into_child_chunks(text.strip())
        plans.append(
            ParentPlan(
                title="全文",
                source_kind="txt_block",
                source_row=None,
                child_texts=children or ([text.strip()] if text.strip() else []),
                preview=text[:1000],
            )
        )
    return [p for p in plans if p.child_texts]


def plans_from_txt(text: str) -> List[ParentPlan]:
    """空行分隔大段：首行短则作标题。"""
    blocks = re.split(r"\n\s*\n+", text.strip())
    plans: List[ParentPlan] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        first_line, _, rest = block.partition("\n")
        if len(first_line) <= 50 and rest.strip():
            title = first_line.strip()
            body = rest.strip()
        else:
            title = first_line.strip()[:80] if len(first_line) <= 80 else "段落"
            body = block
        children = split_into_child_chunks(body)
        if not children and body:
            children = [body]
        plans.append(
            ParentPlan(
                title=title[:500],
                source_kind="txt_block",
                source_row=None,
                child_texts=children,
                preview=body[:1000],
            )
        )
    if not plans and text.strip():
        return plans_from_document_text(text, source_kind="txt")
    return [p for p in plans if p.child_texts]


def build_plans(kind: str, full_text: str, excel_rows: Optional[List[dict]]) -> List[ParentPlan]:
    if kind == "excel" or kind == "csv":
        if excel_rows:
            return plans_from_excel_rows(excel_rows)
        return plans_from_txt(full_text)
    if kind == "txt":
        return plans_from_txt(full_text)
    if kind in ("doc", "pdf"):
        return plans_from_document_text(full_text, "doc" if kind == "doc" else "pdf")
    return plans_from_txt(full_text)
