"""从 Excel/CSV 行提取结构化题库（不直接写库），供统一入库流程使用。"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

def _pick(d: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        for ck in d:
            if ck and k in str(ck):
                v = d.get(ck)
                if v is not None and str(v).strip():
                    return str(v).strip()
    return ""


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_MEANINGLESS_RE = re.compile(r"^[\W_]+$", re.UNICODE)
_PURE_NUM_RE = re.compile(r"^[\[\(（【]?\s*\d+(?:\.\d+)?\s*[\]\)）】]?$")
_OPTION_RE = re.compile(r"^[A-Fa-f](?:\s*[,，/、\s]\s*[A-Fa-f])*$")


def _clean(v: Any) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    s = _URL_RE.sub("", s).replace("|", " ")
    s = re.sub(r"(?:分类|标签|tag|category)\s*[:：]\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -:：;；")
    return s


def _is_meaningless(v: str) -> bool:
    s = _clean(v)
    if not s:
        return True
    if _MEANINGLESS_RE.fullmatch(s):
        return True
    if len(s) <= 2 and all(ch in "-_=*#~.·,，。;；:：" for ch in s):
        return True
    return False


def _norm_diff(v: str) -> str:
    s = _clean(v).lower()
    if s in ("easy", "medium", "hard"):
        return s
    if "易" in s:
        return "easy"
    if "难" in s:
        return "hard"
    return "medium"


def _norm_cat(v: str) -> str:
    s = _clean(v).lower()
    if "project" in s or "项目" in s:
        return "project"
    if "behavior" in s or "行为" in s:
        return "behavior"
    if not s:
        return "未分类"
    return "technical"


def _derive_points(question: str, answer: str, points: str) -> str:
    p = _clean(points)
    if p:
        return p
    words = re.split(r"[，,。；;、\s]+", f"{question} {answer}")
    out: List[str] = []
    for w in words:
        w = _clean(w)
        if len(w) < 2:
            continue
        if w not in out:
            out.append(w)
        if len(out) >= 3:
            break
    return ";".join(out) if out else "综合知识;公共基础"


def _pick_question_type(question: str, options_text: str) -> str:
    q = _clean(question)
    opts = _clean(options_text)
    if opts:
        return "单选题"
    if any(x in q for x in ("判断", "对错", "是否正确", "√", "×")):
        return "判断题"
    if len(q) <= 18:
        return "简单识记"
    return "综合问答"


def _collect_options(row: Dict[str, Any]) -> str:
    items: List[str] = []
    for k, v in row.items():
        kk = str(k or "").strip().lower()
        vv = _clean(v)
        if not vv:
            continue
        if any(t in kk for t in ("选项", "option", "a选", "b选", "c选", "d选")):
            items.append(f"{str(k).strip()}:{vv}")
            continue
        if re.search(r"^(选项)?\s*[a-f]$", kk):
            items.append(f"{str(k).strip()}:{vv}")
    if not items:
        return ""
    dedup: List[str] = []
    for x in items:
        if x not in dedup:
            dedup.append(x)
    return "；".join(dedup)[:1200]


def _is_answer_column_name(col: str) -> bool:
    c = str(col or "").strip().lower()
    if not c:
        return False
    if ("答案" in c) or ("answer" in c):
        # 严禁把题号/序号/行号/页码/id映射到答案字段
        if any(bad in c for bad in ("题号", "序号", "行号", "页码", "编号", "index", "id", "no", "number")):
            return False
        return True
    if ("正确" in c and "选项" in c) or ("正确" in c and "答案" in c):
        return True
    return False


def _extract_answer(row: Dict[str, Any]) -> str:
    # 只从明确的答案列中取值，避免字段映射错误
    for k, v in row.items():
        if _is_answer_column_name(str(k)):
            vv = _clean(v)
            if vv:
                return vv
    return ""


def _normalize_answer(ans: str) -> str:
    s = _clean(ans)
    if not s:
        return "未标注答案"
    # 严禁把题号/行号/括号数字作为答案
    if _PURE_NUM_RE.fullmatch(s):
        return "未标注答案"
    s_upper = s.upper().replace("，", ",").replace("、", ",").replace("/", ",")
    s_upper = re.sub(r"\s+", "", s_upper)
    if _OPTION_RE.fullmatch(s_upper):
        # 多选统一为 A,C 形式；单选为 A
        parts = [x for x in s_upper.split(",") if x]
        dedup: List[str] = []
        for p in parts:
            if p not in dedup:
                dedup.append(p)
        return ",".join(dedup) if dedup else "未标注答案"
    if s in ("√", "×", "对", "错", "正确", "错误"):
        return s
    # 主观题/填空题文本答案允许保留；但纯数字严格禁止
    if re.fullmatch(r"\d+(?:\.\d+)?", s):
        return "未标注答案"
    return s[:1000]


def extract_structured_from_excel_rows(rows: List[dict[str, Any]]) -> Dict[str, List[dict]]:
    """
    识别常见列名并抽取结构化岗位+题目，返回统一数据结构，交由 ingest_pipeline 统一写库。
    """
    jobs_map: Dict[str, dict] = {}
    questions: List[dict] = []
    seen_q: set[tuple[str, str, str]] = set()

    for idx, row in enumerate(rows, start=2):
        non_empty_cells = [v for v in row.values() if _clean(v)]
        if not non_empty_cells:
            continue
        if len(non_empty_cells) == 1 and _is_meaningless(str(non_empty_cells[0])):
            continue

        job_name = _clean(
            _pick(row, "岗位", "岗位名称", "职位", "职位名称", "方向", "job", "position", "角色")
        ) or "通用岗位/基础岗位"

        qtext = _clean(
            _pick(row, "题目", "题干", "问题", "面试题", "question", "question_text")
        )
        # 无明确题目列时，尽量保留可用信息，避免有效行丢失。
        if not qtext:
            candidate_parts = []
            for k, v in row.items():
                key = str(k or "")
                val = _clean(v)
                if not val:
                    continue
                if any(t in key for t in ("备注", "说明", "广告", "链接")):
                    continue
                candidate_parts.append(val)
            if candidate_parts:
                qtext = candidate_parts[0][:500]
        if not qtext:
            continue

        options_text = _collect_options(row)
        if options_text and "选项" not in qtext:
            qtext = f"{qtext}\n选项：{options_text}"

        ans = _normalize_answer(_extract_answer(row))
        diff = _norm_diff(_pick(row, "难度", "difficulty"))
        cat = _norm_cat(_pick(row, "类型", "分类", "类别", "category"))
        q_type = _pick_question_type(qtext, options_text)
        points = _derive_points(qtext, ans, _pick(row, "考点", "知识点", "要点", "标签"))
        tech = _clean(_pick(row, "技术栈", "技能"))
        desc = _clean(_pick(row, "岗位描述", "说明", "职责", "description"))

        dedupe_key = (job_name, qtext, ans or "")
        if dedupe_key in seen_q:
            continue
        seen_q.add(dedupe_key)

        if job_name not in jobs_map:
            tech_list = [x for x in re.split(r"[，,;；、\s]+", tech) if x] if tech else []
            jobs_map[job_name] = {
                "job_name": job_name,
                "tech_stack": tech_list,
                "description": desc or f"{job_name}岗位，强调{('、'.join(tech_list[:6]) if tech_list else '基础能力与项目实践')}。",
            }
        else:
            if tech:
                existed = set(jobs_map[job_name].get("tech_stack") or [])
                for t in [x for x in re.split(r"[，,;；、\s]+", tech) if x]:
                    if t not in existed:
                        jobs_map[job_name]["tech_stack"].append(t)
            if desc and not jobs_map[job_name].get("description"):
                jobs_map[job_name]["description"] = desc

        questions.append(
            {
                "job_name": job_name,
                "content": qtext,
                "answer": ans,
                "difficulty": diff,
                "exam_points": f"{points};{q_type}"[:500] if points else q_type,
                "category": cat or "未分类",
                "source_row": idx,
            }
        )

    return {"jobs": list(jobs_map.values()), "questions": questions}
