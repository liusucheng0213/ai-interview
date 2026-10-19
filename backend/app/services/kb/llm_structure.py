"""
AI 结构化抽取：从全文抽取岗位、技术栈、题目等，仅用于写入 MySQL，不混入向量子块正文。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

PROMPT_KB_STRUCTURE = """你是面试题库结构化引擎。根据原始文档摘录（可能截断），抽取高质量题库数据。
严格要求：
1) 只保留可用于问答训练的核心内容。
2) 删除链接、分类标签、广告语、格式符号垃圾。
3) 每条 question 必须包含：job_name、content、answer、exam_points、difficulty、category。
4) exam_points 必须非空；若原文未直接给出，请依据题目与答案提炼 1~3 个考点（分号分隔）。
5) 不要输出 markdown，不要输出解释文字。

必须输出**唯一**一个 JSON 对象（不要 markdown），格式如下：
{{
  "jobs": [
    {{
      "job_name": "岗位名称",
      "tech_stack": ["技术1", "技术2"],
      "description": "岗位简述"
    }}
  ],
  "questions": [
    {{
      "job_name": "所属岗位名称（须与 jobs 中某项一致或最接近）",
      "content": "面试题目",
      "answer": "参考答案",
      "difficulty": "easy|medium|hard",
      "exam_points": "考点A;考点B",
      "category": "technical|project|behavior"
    }}
  ],
  "relations": [
    {{"subject": "实体/概念1", "predicate": "关系类型", "object": "实体/概念2"}}
  ]
}}

规则：
1. 若原文主要是叙述性文档，可归纳 1~3 个岗位并生成对应题目。
2. tech_stack 仅保留简短技术关键词，去重后最多 20 个。
3. relations 为可选，不要编造。
4. question.content 不得包含 URL、标签词（如“分类:”“标签:”）、多余前缀。

原始文档摘录：
---
{content}
---
"""

PROMPT_KB_STRUCTURE_SYSTEM = (
    "你是知识图谱与题库结构化抽取模型，仅输出合法 JSON；"
    "关系三元组与题目均以原文为依据，禁止臆造。"
)


async def structured_extract(text: str, max_chars: int = 14000) -> Dict[str, Any]:
    snippet = (text or "")[:max_chars]
    if not snippet.strip():
        return {"jobs": [], "questions": []}

    try:
        from config.llm_conf import call_llm, MODEL_KNOWLEDGE_GRAPH

        prompt = PROMPT_KB_STRUCTURE.format(content=snippet)
        raw = await call_llm(
            prompt=prompt,
            system_prompt=PROMPT_KB_STRUCTURE_SYSTEM,
            model=MODEL_KNOWLEDGE_GRAPH,
        )
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {"jobs": [], "questions": []}
        data.setdefault("jobs", [])
        data.setdefault("questions", [])
        data.setdefault("relations", [])
        return _sanitize_structured_data(data)
    except Exception as e:
        logger.warning(f"[RAG v2] LLM 结构化抽取失败: {e}")
        return {"jobs": [], "questions": [], "relations": []}


def merge_tech_keywords(text: str, jobs: List[dict]) -> List[dict]:
    """无 LLM 时弱回退：不新建题目，仅补空 tech_stack。"""
    return jobs


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_TAG_RE = re.compile(r"(?:分类|标签|tag|category)\s*[:：]\s*", re.IGNORECASE)
_NOISE_RE = re.compile(r"[`~^*_#]{2,}")
_SPACES_RE = re.compile(r"\s+")
_PURE_NUM_RE = re.compile(r"^[\[\(（【]?\s*\d+(?:\.\d+)?\s*[\]\)）】]?$")
_OPTION_RE = re.compile(r"^[A-Fa-f](?:\s*[,，/、\s]\s*[A-Fa-f])*$")
_DIFF_MAP = {"易": "easy", "中": "medium", "难": "hard"}
_CAT_MAP = {
    "技术": "technical",
    "technical": "technical",
    "项目": "project",
    "project": "project",
    "行为": "behavior",
    "behavior": "behavior",
}


def _clean_text(v: Any, max_len: int = 5000) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    s = _URL_RE.sub("", s)
    s = _TAG_RE.sub("", s)
    s = _NOISE_RE.sub(" ", s)
    s = s.replace("|", " ").replace("\r", " ").replace("\n", " ")
    s = _SPACES_RE.sub(" ", s).strip(" -:：;；")
    return s[:max_len]


def _normalize_diff(v: Any) -> str:
    s = _clean_text(v, max_len=32).lower()
    if not s:
        return "medium"
    if s in ("easy", "medium", "hard"):
        return s
    for k, vv in _DIFF_MAP.items():
        if k in s:
            return vv
    return "medium"


def _normalize_cat(v: Any) -> str:
    s = _clean_text(v, max_len=64).lower()
    if not s:
        return "technical"
    if s in _CAT_MAP:
        return _CAT_MAP[s]
    for k, vv in _CAT_MAP.items():
        if k in s:
            return vv
    return "technical"


def _derive_exam_points(question: str, answer: str, fallback: str = "") -> str:
    base = _clean_text(fallback, max_len=256)
    if base:
        return base
    words = re.split(r"[，,。；;、\s]+", f"{question} {answer}")
    picked: List[str] = []
    for w in words:
        w = _clean_text(w, max_len=30)
        if len(w) < 2:
            continue
        if any(x in w.lower() for x in ("什么", "如何", "为什么", "请", "描述", "回答")):
            continue
        if w not in picked:
            picked.append(w)
        if len(picked) >= 3:
            break
    return ";".join(picked) if picked else "基础原理;应用实践"


def _normalize_answer(v: Any) -> str:
    s = _clean_text(v, max_len=1000)
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


def _sanitize_structured_data(data: Dict[str, Any]) -> Dict[str, Any]:
    jobs_in = data.get("jobs") or []
    questions_in = data.get("questions") or []
    relations = data.get("relations") or []

    jobs: List[Dict[str, Any]] = []
    job_names: List[str] = []
    for j in jobs_in:
        if not isinstance(j, dict):
            continue
        name = _clean_text(j.get("job_name"), max_len=128)
        if not name:
            continue
        tech_raw = j.get("tech_stack")
        tech_list: List[str] = []
        if isinstance(tech_raw, list):
            tech_list = [_clean_text(x, max_len=64) for x in tech_raw]
        elif isinstance(tech_raw, str):
            tech_list = [_clean_text(x, max_len=64) for x in re.split(r"[，,;；、\s]+", tech_raw)]
        tech = []
        for t in tech_list:
            if t and t not in tech:
                tech.append(t)
        desc = _clean_text(j.get("description"), max_len=2000)
        if not desc:
            desc = f"{name}岗位，核心关注{('、'.join(tech[:6]) if tech else '基础能力与项目实践')}。"
        jobs.append({"job_name": name, "tech_stack": tech[:20], "description": desc})
        job_names.append(name)

    if not job_names:
        job_names = ["通用技术岗位"]
        jobs = [
            {
                "job_name": "通用技术岗位",
                "tech_stack": [],
                "description": "通用技术岗位，覆盖基础原理、工程实践与问题分析能力。",
            }
        ]

    clean_questions: List[Dict[str, Any]] = []
    seen_q: set[tuple[str, str, str]] = set()
    for q in questions_in:
        if not isinstance(q, dict):
            continue
        content = _clean_text(q.get("content"), max_len=1200)
        answer = _normalize_answer(q.get("answer"))
        job_name = _clean_text(q.get("job_name"), max_len=128) or job_names[0]
        if job_name not in job_names:
            job_name = job_names[0]
        dedupe_key = (job_name, content, answer)
        if not content or dedupe_key in seen_q:
            continue
        seen_q.add(dedupe_key)
        exam_points = _derive_exam_points(content, answer, q.get("exam_points"))
        clean_questions.append(
            {
                "job_name": job_name,
                "content": content,
                "answer": answer,
                "difficulty": _normalize_diff(q.get("difficulty")),
                "exam_points": exam_points,
                "category": _normalize_cat(q.get("category")),
            }
        )

    return {"jobs": jobs, "questions": clean_questions, "relations": relations}
