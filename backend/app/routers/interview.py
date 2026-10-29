"""
面试路由模块

端点列表：
  POST /api/interview/start                  开始面试（返回第一个问题）
  POST /api/interview/answer/text            提交文字回答（非流式，向后兼容）
  POST /api/interview/answer/text/stream     提交文字回答（SSE 流式，打字机效果）
  POST /api/interview/answer/speech          提交语音回答
  POST /api/interview/answer/video           提交视频回答（含表情分析）
  POST /api/interview/answer/video/stream    实时视频流上传（分片）
  GET  /api/interview/history                获取面试历史列表
  GET  /api/interview/detail/{interview_id}  获取面试详情
  GET  /api/interview/stats                  获取面试统计
  POST /api/interview/end                    结束面试，生成 AI 评估报告
  GET  /api/interview/download/{id}          下载面试报告
"""

import base64
import json
import logging
import os
import tempfile
import re
from html import escape
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from config.env_util import env_int
from crud.history import (
    create_history,
    add_content_history,
    search_now_history,
    create_assessment,
    get_user_history,
    count_interviews_by_mode,
    add_rd,
    get_interview_by_id,
    get_evaluation_report_by_id,
    search_rd,
    _deserialize_list,
    build_interview_detail_payload,
    dimension_scores_from_values,
    _safe_improvement_resources,
)
from crud.resume import get_user_resumes
from models.users import User
from schemas.interview import TextAnswerRequest, InterviewStartRequest
import asyncio

from services.LLM_services import (
    generate_interview_question,
    generate_interview_question_stream,
    generate_final_report,
    speech_to_text,
    analyze_video_expression,
    transcribe_speech,
    evaluate_answer,
    analyze_speech_features,
)
from services.kb.rag_plan1 import retrieve_context
from utils.auth import get_current_user
from models.rag_schema import Job as RagJob

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interview")


# ==================== 工具函数 ====================

def _assert_same_interview(interview_id, history) -> None:
    """语音/视频表单里的 interview_id 必须对上当前这场，避免答到别的进行中记录。"""
    if interview_id is None:
        return
    text = str(interview_id).strip()
    if text.lower() in {"", "none", "null", "undefined"}:
        return
    try:
        parsed = int(text)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="interview_id 无效")
    if parsed != history.id:
        raise HTTPException(status_code=400, detail="interview_id 与当前进行中的面试不一致")


def _extract_last_ai_question(chat_context: str) -> str:
    """从对话历史中提取最近一条面试官问题（用于评估上下文）"""
    if not chat_context:
        return ""
    lines = [l.strip() for l in chat_context.strip().split("\n") if l.strip()]
    for line in reversed(lines):
        if line.startswith("ai面试官：") or line.startswith("面试官："):
            return line.replace("ai面试官：", "").replace("面试官：", "").strip()
    return ""


def _strip_llm_json_fence(text: str) -> str:
    """去掉模型输出外层的 markdown 代码块（勿用 lstrip('`json')，会把参数当字符集误剥）。"""
    s = (text or "").strip()
    low = s.lower()
    if "```json" in low:
        start = low.index("```json") + len("```json")
        rest = s[start:]
        end = rest.find("```")
        return (rest[:end] if end >= 0 else rest).strip()
    if s.startswith("```"):
        rest = s.split("```", 2)
        inner = rest[1] if len(rest) >= 2 else ""
        inner = inner.strip()
        if inner.lower().startswith("json"):
            inner = inner[4:].lstrip("\n\r \t").strip()
        return inner
    return s


def _first_balanced_json_object(text: str) -> Optional[str]:
    """从首个「{」起做括号平衡截取，字符串内括号不计入（仅支持 JSON 双引号字符串）。"""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    i = start
    in_str = False
    escape = False
    while i < len(text):
        c = text[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1
    return None


def _strip_trailing_commas_json(text: str) -> str:
    """移除 `,` 后紧跟 `}` 或 `]` 的尾部逗号（常见模型笔误），忽略字符串内内容。"""
    out: list[str] = []
    in_str = False
    escape = False
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
            continue
        if c == "," and i + 1 < n:
            j = i + 1
            while j < n and text[j] in " \t\n\r":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_llm_json_object(raw: str) -> dict:
    """
    解析模型返回的 JSON 对象：去围栏、截取最外层对象、必要时修尾部逗号。
    失败时抛出 json.JSONDecodeError（由调用方记录并转为 HTTP 错误）。
    """
    candidates: list[str] = []
    stripped = _strip_llm_json_fence(raw)
    if stripped:
        candidates.append(stripped)
    if raw and raw.strip() not in candidates:
        candidates.append(raw.strip())
    last_err: Optional[Exception] = None
    for blob in candidates:
        for attempt in (
            blob,
            _strip_trailing_commas_json(blob),
        ):
            sub = _first_balanced_json_object(attempt) or attempt.strip()
            try:
                obj = json.loads(sub)
            except json.JSONDecodeError as e:
                last_err = e
                continue
            if isinstance(obj, dict):
                return obj
            last_err = json.JSONDecodeError("顶层必须是 JSON 对象", sub, 0)
    if last_err:
        raise last_err
    raise json.JSONDecodeError("Empty or non-object JSON", raw or "", 0)


async def _get_rag_knowledge(
    query: str,
    job_id: int,
    db: AsyncSession,
    top_k: int = 3,
) -> str:
    """
    安全封装的 RAG 检索，同时检索岗位题库和用户上传的知识库，合并返回。

    Returns:
        检索到的知识文本（多条用分隔符拼接），或空字符串
    """
    try:
        rag = await retrieve_context(
            db=db,
            query=query.strip(),
            filter_data={"job_id": str(job_id)},
        )
        chunks = rag.get("chunks", [])[: max(top_k, 1)]
        if not chunks:
            return ""
        results = [str(c.get("content", "")).strip() for c in chunks if str(c.get("content", "")).strip()]
        return "\n---\n".join(results[:top_k]) if results else ""
    except Exception as e:
        logger.warning(f"[RAG] 检索失败，跳过：{e}")
        return ""


async def _require_job_by_id(db: AsyncSession, job_id: int) -> RagJob:
    row = await db.get(RagJob, job_id)
    if not row:
        raise HTTPException(status_code=400, detail="job_id 不存在")
    return row


def _render_report_html(
    *,
    position_name: str,
    overall_score: float,
    radar: list[dict],
    question_analysis: list[dict],
    suggestions: list[str],
    rag_evidence: str,
    improvement_resources: Optional[dict] = None,
) -> str:
    radar_json = json.dumps(radar, ensure_ascii=False)
    qa_rows = "".join(
        [
            "<tr>"
            f"<td>{idx + 1}</td>"
            f"<td>{escape(str(it.get('question', '')))}</td>"
            f"<td>{escape(str(it.get('score', '')))}</td>"
            f"<td>{escape(str(it.get('correctness', '')))}</td>"
            f"<td>{escape(str(it.get('completeness', '')))}</td>"
            f"<td>{escape('；'.join(it.get('missing_points', []) or []))}</td>"
            f"<td>{escape('；'.join(it.get('errors', []) or []))}</td>"
            f"<td>{escape(str(it.get('feedback', '')))}</td>"
            "</tr>"
            for idx, it in enumerate(question_analysis)
        ]
    )
    sug_html = "".join([f"<li>{escape(s)}</li>" for s in suggestions])
    ir = improvement_resources if isinstance(improvement_resources, dict) else {}
    kp = ir.get("knowledge_points") or []
    siq = ir.get("sample_interview_questions") or []
    cr = ir.get("communication_readings") or []
    ir_parts = []
    if isinstance(kp, list) and kp:
        items = "".join(
            f"<li><b>{escape(str(it.get('topic','')))}</b>：{escape(str(it.get('summary','')))}"
            f"（行动：{escape(str(it.get('action','')))}）</li>"
            for it in kp[:12]
            if isinstance(it, dict)
        )
        ir_parts.append(f"<div class='card'><h3>巩固知识点</h3><ul>{items}</ul></div>")
    if isinstance(siq, list) and siq:
        items = "".join(
            f"<li><b>{escape(str(it.get('question','')))}</b> — 考察：{escape(str(it.get('focus','')))}</li>"
            for it in siq[:12]
            if isinstance(it, dict)
        )
        ir_parts.append(f"<div class='card'><h3>推荐练习面试题</h3><ul>{items}</ul></div>")
    if isinstance(cr, list) and cr:
        items = "".join(
            f"<li><b>{escape(str(it.get('title','')))}</b>：{escape(str(it.get('summary','')))}"
            f" — {escape(str(it.get('url_or_search','') or it.get('url','')))}</li>"
            for it in cr[:8]
            if isinstance(it, dict)
        )
        ir_parts.append(f"<div class='card'><h3>沟通与表达延伸阅读</h3><ul>{items}</ul></div>")
    ir_html = "".join(ir_parts)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>面试评估报告</title>"
        "<style>body{font-family:Arial;padding:24px;color:#1f2937;}h1{margin:0 0 8px;}table{width:100%;border-collapse:collapse;margin-top:16px;}th,td{border:1px solid #d1d5db;padding:8px;text-align:left;font-size:13px;}th{background:#f3f4f6;} .card{border:1px solid #e5e7eb;padding:12px;border-radius:8px;margin-top:12px;}</style>"
        "</head><body>"
        f"<h1>面试评估报告</h1><div>岗位：{escape(position_name)}</div><div>综合得分：{overall_score:.2f}</div>"
        f"<div class='card'><h3>雷达图数据</h3><pre>{escape(radar_json)}</pre></div>"
        "<div class='card'><h3>逐题分析</h3><table><thead><tr><th>#</th><th>题目</th><th>得分</th><th>正确性</th><th>完整性</th><th>遗漏点</th><th>错误点</th><th>反馈</th></tr></thead><tbody>"
        f"{qa_rows}</tbody></table></div>"
        f"<div class='card'><h3>改进建议</h3><ul>{sug_html}</ul></div>"
        f"{ir_html}"
        f"<div class='card'><h3>知识点依据</h3><pre>{escape(rag_evidence)}</pre></div>"
        "</body></html>"
    )


async def _build_question_analysis_array(
    *,
    position_name: str,
    qa_records: list[dict],
    job_id: int,
    session_meta: dict,
    db: AsyncSession,
) -> list[dict]:
    out: list[dict] = []
    for qa in qa_records:
        q = str(qa.get("question") or "").strip()
        a = str(qa.get("answer") or "").strip()
        if not q:
            continue
        rag = await _get_rag_knowledge(
            query=f"{q}\n{a}"[:1200],
            job_id=job_id,
            db=db,
            top_k=3,
        )
        eva = await evaluate_answer(
            position_name,
            a or "（未作答）",
            q,
            rag_context=rag,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=session_meta.get("candidate_context") or None,
        )
        qa_obj = eva.get("question_analysis") or {}
        if not isinstance(qa_obj, dict):
            raise HTTPException(status_code=500, detail="逐题分析结构错误")
        score = float(eva.get("overall") or 0.0)
        out.append(
            {
                "question": q,
                "answer": a,
                "correctness": str(qa_obj.get("correctness") or ""),
                "completeness": str(qa_obj.get("completeness") or ""),
                "missing_points": list(qa_obj.get("missing_points") or []),
                "errors": list(qa_obj.get("errors") or []),
                "feedback": str(eva.get("tip") or eva.get("weakness") or ""),
                "score": score,
            }
        )
    return out


def _early_termination_check(eval_result: dict, round_num: int) -> tuple:
    """
    多轮表现持续极差时，由系统提前结束面试。
    round_num 为 add_rd 返回的当前轮次（随每次作答递增）。
    """
    if not eval_result:
        return False, "", ""
    try:
        ov = float(eval_result.get("overall"))
    except (TypeError, ValueError):
        return False, "", ""
    w = (eval_result.get("weakness") or "").strip()
    t = (eval_result.get("tip") or "").strip()
    sug = (f"{w} {t}".strip()) or "建议对照岗位要求系统复习核心知识点，并练习用「结论—理由—例子」结构作答。"
    if round_num >= 7 and ov < 4.0:
        return (
            True,
            "多轮回答在核心能力与岗位匹配上持续未达合格基线，继续延长面试时间难以改变评估结论。",
            sug,
        )
    if round_num >= 5 and ov < 3.6:
        return True, "根据近两轮综合评分，当前表现与岗位预期差距较大，本轮测评提前结束。", sug
    if round_num >= 4 and ov < 3.0:
        return True, "本轮回答在技术准确性与岗位相关性上严重不足，已不具备继续深入考察的基础。", sug
    return False, "", ""


async def run_interview_completion(user: User, db: AsyncSession) -> dict:
    """
    结束当前进行中的面试并生成 AI 报告（与 POST /interview/end 逻辑一致）。
    调用前请确保已在 chat_context 中写入结束说明（若为提前结束）。
    """
    logger.info(f"[结束面试] 用户：{user.username}")

    history = await search_now_history(user, db)
    if not history:
        raise HTTPException(status_code=404, detail="未找到进行中的面试记录")

    position_name = history.position_name
    job_id = history.job_id
    difficulty = history.difficulty
    conversation = history.chat_context or ""
    session_meta = _extract_session_meta(conversation)
    conv_for_llm = _conversation_for_llm(conversation)
    standard_rag = await _get_rag_knowledge(
        query="岗位标准答案 核心能力 评分依据",
        job_id=job_id,
        db=db,
        top_k=6,
    )

    logger.info("[结束面试] 调用 AI 生成评估报告...")
    report_raw = await generate_final_report(
        position_name,
        difficulty,
        conv_for_llm,
        rag_context=standard_rag,
        language=session_meta["language"],
        candidate_context=session_meta.get("candidate_context") or None,
    )

    def _safe_float(val, fallback=None):
        if val is None:
            return fallback
        try:
            return float(val)
        except (TypeError, ValueError):
            return fallback

    content_score = _safe_float(report_raw.get("content_score"), 6.0)
    expression_score = _safe_float(report_raw.get("expression_score"), 6.0)
    technical_correctness = _safe_float(report_raw.get("technical_correctness_score"))
    knowledge_depth = _safe_float(report_raw.get("knowledge_depth_score"))
    job_match_score = _safe_float(report_raw.get("job_match_score"))
    logic_score = _safe_float(report_raw.get("logic_score"))
    communication_score = _safe_float(report_raw.get("communication_score"))
    adaptability_score = _safe_float(report_raw.get("adaptability_score"))
    speech_rate_score = _safe_float(report_raw.get("speech_rate_score"))
    clarity_score = _safe_float(report_raw.get("clarity_score"))
    confidence_score = _safe_float(report_raw.get("confidence_score"))

    overall_raw = _safe_float(report_raw.get("overall_score"))
    if overall_raw is not None:
        overall_score = round(overall_raw, 2)
    else:
        valid_scores = [s for s in [
            content_score,
            expression_score,
            technical_correctness,
            knowledge_depth,
            logic_score,
            job_match_score,
            communication_score,
            adaptability_score,
            speech_rate_score,
            clarity_score,
            confidence_score,
        ] if s is not None]
        overall_score = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else 6.0

    _rm = report_raw.get("report_markdown")
    report_markdown_val = _rm.strip() if isinstance(_rm, str) and _rm.strip() else None

    if not isinstance(report_raw.get("highlights"), list) or not isinstance(report_raw.get("weaknesses"), list) or not isinstance(report_raw.get("suggestions"), list):
        raise HTTPException(status_code=500, detail="报告结构错误：highlights/weaknesses/suggestions 必须为数组")
    report_data = {
        "content_score": content_score,
        "expression_score": expression_score,
        "technical_correctness_score": technical_correctness,
        "knowledge_depth_score": knowledge_depth,
        "logic_score": logic_score,
        "job_match_score": job_match_score,
        "communication_score": communication_score,
        "adaptability_score": adaptability_score,
        "speech_rate_score": speech_rate_score,
        "clarity_score": clarity_score,
        "confidence_score": confidence_score,
        "total_score": overall_score,
        "highlights": report_raw.get("highlights"),
        "weaknesses": report_raw.get("weaknesses"),
        "suggestions": report_raw.get("suggestions"),
        "report_markdown": report_markdown_val,
        "improvement_resources": report_raw.get("improvement_resources") or {},
    }

    report_data["rag_evidence"] = standard_rag
    logger.info(f"[结束面试] 报告已保存，总分：{overall_score}")

    qa_records = []
    if conversation:
        lines = [l for l in conversation.strip().split("\n") if l.strip()]
        # 首行 [SESSION_META] 不参与「一问一答」配对，否则会把元信息错当成题目
        if lines and lines[0].startswith("[SESSION_META]"):
            lines = lines[1:]
        for i in range(0, len(lines) - 1, 2):
            if i + 1 < len(lines):
                q_line = lines[i]
                if not (q_line.startswith("ai面试官：") or q_line.startswith("面试官：")):
                    continue
                raw_answer = lines[i + 1]
                j = i + 2
                while j < len(lines) and not lines[j].startswith("ai面试官：") and not lines[j].startswith("面试官："):
                    raw_answer += " " + lines[j]
                    j += 1
                qa_records.append({
                    "question": q_line.replace("ai面试官：", "").replace("面试官：", ""),
                    "answer": raw_answer
                        .replace("候选人：", "")
                        .replace("候选人（语音）：", "")
                        .replace("候选人（视频）：", "")
                        .replace("表情分析：", "[表情] ")
                        .replace("心理状态：", "[状态] ")
                        .replace("肢体语言：", "[肢体] ")
                        .replace("回答内容：", "")
                        .strip(),
                })

    resume_match_score = _safe_float(report_raw.get("resume_match_score"))
    dimension_scores = dimension_scores_from_values(
        content_score=content_score,
        technical_correctness_score=technical_correctness,
        knowledge_depth_score=knowledge_depth,
        logic_score=logic_score,
        job_match_score=job_match_score,
        communication_score=communication_score,
        adaptability_score=adaptability_score,
        speech_rate_score=speech_rate_score,
        clarity_score=clarity_score,
        confidence_score=confidence_score,
        expression_score=expression_score,
        resume_match_score=resume_match_score,
    )
    if technical_correctness is not None and knowledge_depth is not None:
        technical_mastery = (technical_correctness + knowledge_depth) / 2.0
    elif technical_correctness is not None:
        technical_mastery = technical_correctness
    elif knowledge_depth is not None:
        technical_mastery = knowledge_depth
    else:
        technical_mastery = content_score

    question_analysis = await _build_question_analysis_array(
        position_name=position_name,
        qa_records=qa_records,
        job_id=job_id,
        session_meta=session_meta,
        db=db,
    )
    report_data["question_analysis"] = question_analysis
    report_data["dimension_feedback"] = report_raw.get("dimension_feedback", {})
    report_html = _render_report_html(
        position_name=position_name,
        overall_score=overall_score,
        radar=dimension_scores,
        question_analysis=question_analysis,
        suggestions=report_data["suggestions"] if isinstance(report_data["suggestions"], list) else _deserialize_list(report_data["suggestions"]),
        rag_evidence=standard_rag,
        improvement_resources=report_data.get("improvement_resources"),
    )
    report_data["report_html"] = report_html
    await create_assessment(user, report_data, db)

    full_report = {
        "overall_score": overall_score,
        "technical_mastery": technical_mastery,
        "dimension_scores": dimension_scores,
        "dimension_feedback": report_raw.get("dimension_feedback", {}),
        "improvement_resources": report_data.get("improvement_resources") or {},
        "rag_evidence": report_raw.get("rag_evidence", standard_rag),
        "question_analysis": question_analysis,
        "qa_records": qa_records,
        "highlights": report_data["highlights"] if isinstance(report_data["highlights"], list) else _deserialize_list(report_data["highlights"]),
        "weaknesses": report_data["weaknesses"] if isinstance(report_data["weaknesses"], list) else _deserialize_list(report_data["weaknesses"]),
        "suggestions": report_data["suggestions"] if isinstance(report_data["suggestions"], list) else _deserialize_list(report_data["suggestions"]),
        "report_markdown": report_markdown_val,
        "report_html": report_html,
    }

    return {
        "report": full_report,
        "message": "面试已结束，AI 评估报告已生成",
    }


def _build_session_meta(
    interviewer_style: str,
    language: str,
    candidate_context: Optional[str] = None,
) -> str:
    """构造会话元信息行，写入 chat_context 首行。候选人背景以 base64 附加，避免换行破坏解析。"""
    style = interviewer_style if interviewer_style in {"rigorous", "pressure", "heuristic"} else "rigorous"
    lang = language if language in {"zh", "en", "bilingual"} else "zh"
    meta = f"[SESSION_META] style={style}; language={lang}"
    ctx = (candidate_context or "").strip()
    if ctx:
        raw = ctx[:12000].encode("utf-8")
        meta += "; ctx_b64=" + base64.b64encode(raw).decode("ascii")
    return meta + "\n"


def _extract_session_meta(chat_context: str) -> dict:
    """从 chat_context 中读取会话元信息，兼容无元信息的旧会话。"""
    defaults: dict = {"interviewer_style": "rigorous", "language": "zh", "candidate_context": ""}
    if not chat_context:
        return defaults
    first_line = chat_context.split("\n", 1)[0].strip()
    if not first_line.startswith("[SESSION_META]"):
        return defaults

    style_match = re.search(r"style=([a-zA-Z_]+)", first_line)
    language_match = re.search(r"language=([a-zA-Z_]+)", first_line)
    ctx_match = re.search(r"ctx_b64=([A-Za-z0-9+/=]+)", first_line)
    style = style_match.group(1) if style_match else defaults["interviewer_style"]
    language = language_match.group(1) if language_match else defaults["language"]

    if style not in {"rigorous", "pressure", "heuristic"}:
        style = defaults["interviewer_style"]
    if language not in {"zh", "en", "bilingual"}:
        language = defaults["language"]
    out = {"interviewer_style": style, "language": language, "candidate_context": ""}
    if ctx_match:
        try:
            out["candidate_context"] = base64.b64decode(ctx_match.group(1).encode("ascii")).decode("utf-8")
        except Exception:
            out["candidate_context"] = ""
    return out


def _conversation_for_llm(chat_context: str) -> str:
    """去掉首行 SESSION_META，供 LLM 作为「对话历史」使用。"""
    if not chat_context:
        return ""
    lines = chat_context.strip().split("\n")
    if lines and lines[0].startswith("[SESSION_META]"):
        return "\n".join(lines[1:]).strip()
    return chat_context.strip()


async def _default_profile_and_resume_text(user: User, db: AsyncSession) -> tuple[str, str]:
    """从账号资料与最新简历生成默认上下文文本。"""
    from routers.resume import generate_resume_text

    bits = []
    if getattr(user, "major", None):
        bits.append(f"专业/方向：{user.major}")
    if getattr(user, "signature", None):
        bits.append(f"个人简介：{user.signature}")
    if getattr(user, "hobbies", None):
        bits.append(f"兴趣爱好：{user.hobbies}")
    g = getattr(user, "gender", None) or ""
    if g:
        bits.append(f"性别：{g}")
    profile = "\n".join(bits) if bits else ""

    resume_txt = ""
    resumes = await get_user_resumes(db, user.id)
    if resumes:
        r = resumes[0]
        if getattr(r, "optimized_basic_info", None):
            payload = {
                "basic_info": r.optimized_basic_info or {},
                "education": r.optimized_education or [],
                "experience": r.optimized_experience or [],
                "projects": r.optimized_projects or [],
                "skills": r.optimized_skills or [],
            }
        else:
            payload = {
                "basic_info": r.basic_info or {},
                "education": r.education or [],
                "experience": r.experience or [],
                "projects": r.projects or [],
                "skills": r.skills or [],
            }
        try:
            resume_txt = generate_resume_text(payload)
            sep = "\n" + "=" * 50 + "\n\n"
            if sep in resume_txt:
                resume_txt = resume_txt.split(sep, 1)[-1]
        except Exception as e:
            logger.warning(f"[面试上下文] 简历文本生成失败：{e}")
    return profile, resume_txt


def _merge_interview_context(
    request_profile: Optional[str],
    request_resume: Optional[str],
    default_profile: str,
    default_resume: str,
) -> str:
    """合并用户自定义与默认的个人资料、简历摘要，作为候选人背景。"""
    prof = (request_profile.strip() if request_profile is not None else None)
    if prof is None:
        prof = (default_profile or "").strip()
    else:
        prof = prof[:8000]

    res = (request_resume.strip() if request_resume is not None else None)
    if res is None:
        res = (default_resume or "").strip()
    else:
        res = res[:8000]

    parts = []
    if prof:
        parts.append("【个人资料】\n" + prof)
    if res:
        parts.append("【简历摘要】\n" + res)
    return "\n\n".join(parts)


# ==================== 开始面试 ====================

@router.post("/start", summary="开始面试")
async def start_interview(
    request: InterviewStartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    开始一场新的面试，返回面试 ID 和第一个问题。

    - **position_name**: 岗位名称（如：Java 后端）
    - **mode**: 面试形式（text/speech/video）
    - **difficulty**: 面试难度（entry/intermediate/expert）
    """
    logger.info(
        f"[开始面试] 用户：{user.username}，job_id：{request.job_id}，模式：{request.mode}，"
        f"难度：{request.difficulty}，风格：{request.interviewer_style}，语言：{request.language}"
    )
    if not request.job_id:
        raise HTTPException(status_code=400, detail="job_id 必填")
    job_row = await _require_job_by_id(db, request.job_id)
    position_name = job_row.job_name
    history = await create_history(user, request.job_id, position_name, request.difficulty, request.mode, db)
    def_prof, def_resume = await _default_profile_and_resume_text(user, db)
    merged_ctx = _merge_interview_context(
        request.profile_context,
        request.resume_context,
        def_prof,
        def_resume,
    )
    session_meta = _build_session_meta(
        request.interviewer_style,
        request.language,
        candidate_context=merged_ctx or None,
    )
    await add_content_history(user, session_meta, db, history=history)

    meta_now = _extract_session_meta(session_meta)
    rag_knowledge = await _get_rag_knowledge(
        f"{position_name} 技术栈 面试题 考点",
        request.job_id,
        db,
        top_k=4,
    )
    first_question = await generate_interview_question(
        position_name,
        request.difficulty,
        "",
        1,
        rag_knowledge=rag_knowledge or None,
        interviewer_style=request.interviewer_style,
        language=request.language,
        candidate_context=meta_now.get("candidate_context") or None,
    )

    await add_content_history(user, f"ai面试官：{first_question}\n", db)

    return {
        "interview_id": history.id,
        "job_id": request.job_id,
        "message": "面试开始成功",
        "position_name": position_name,
        "question": first_question,
        "interviewer_style": request.interviewer_style,
        "language": request.language,
    }


# ==================== 提交文字回答（非流式） ====================

@router.post("/answer/text", summary="提交文字回答（非流式）")
async def submit_text_answer(
    request: TextAnswerRequest,
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    提交用户对面试问题的文字回答，返回完整的下一个问题。

    保持向后兼容，前端无需强制升级到流式接口。
    """
    logger.info(f"[文字回答] 用户：{user.username}，内容预览：{request.answer[:50]}...")

    try:
        history = await search_now_history(user, db)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录，请先开始面试")
        if history.job_id != job_id:
            raise HTTPException(status_code=403, detail="job_id 与当前面试不一致")
        if request.interview_id is not None and request.interview_id != history.id:
            raise HTTPException(status_code=400, detail="interview_id 与当前进行中的面试不一致")

        position_name = history.position_name
        job_id = history.job_id
        difficulty = history.difficulty
        session_meta = _extract_session_meta(history.chat_context)

        rd = await add_rd(user, db)

        # 传入已有 history 对象，避免内部重复查询
        history = await add_content_history(user, f"候选人：{request.answer}\n", db, history=history)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")

        rag_knowledge = await _get_rag_knowledge(
            request.answer,
            job_id,
            db,
            top_k=3,
        )
        logger.info(f"[RAG] 检索完成，知识长度：{len(rag_knowledge)}")

        # 提取最近一个面试官问题（用于评估上下文）
        last_question = _extract_last_ai_question(history.chat_context)

        cc = session_meta.get("candidate_context") or None
        answer_analysis = await evaluate_answer(
            position_name,
            request.answer,
            last_question,
            rag_context=rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )
        early, end_reason, end_suggestions = _early_termination_check(answer_analysis, rd)
        if early:
            closing = (
                f"ai面试官：感谢您参加本次模拟面试。根据当前测评结果，本场面试将提前结束。\n"
                f"【主要原因】{end_reason}\n"
                f"【改进建议】{end_suggestions}\n"
            )
            await add_content_history(user, closing, db, history=history)
            completion = await run_interview_completion(user, db)
            return {
                "interview_ended": True,
                "end_reason": end_reason,
                "end_suggestions": end_suggestions,
                "answer_analysis": answer_analysis,
                "report": completion.get("report"),
                "message": completion.get("message"),
            }

        next_question = await generate_interview_question(
            position_name,
            difficulty,
            _conversation_for_llm(history.chat_context),
            rd,
            rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )

        await add_content_history(user, f"ai面试官：{next_question}\n", db, history=history)

        return {
            "next_question": next_question,
            "answer_analysis": answer_analysis,
            "interview_ended": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[文字回答] 系统异常：{type(e).__name__} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理回答时发生错误：{e}")


# ==================== 提交文字回答（SSE 流式） ====================

@router.post("/answer/text/stream", summary="提交文字回答（SSE 流式输出）")
async def submit_text_answer_stream(
    request: TextAnswerRequest,
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    提交文字回答，以 SSE（Server-Sent Events）流式返回下一个面试问题。

    前端使用 fetch + ReadableStream 接收，实现打字机效果。

    SSE 事件格式：
      data: {"type": "chunk", "text": "文本片段"}\\n\\n
      data: {"type": "done",  "full_text": "完整问题"}\\n\\n
      data: {"type": "error", "message": "错误信息"}\\n\\n
    """
    logger.info(f"[文字回答-流式] 用户：{user.username}，内容预览：{request.answer[:50]}...")

    # --- 在生成器之外完成所有 DB 预操作 ---
    try:
        history = await search_now_history(user, db)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录，请先开始面试")
        if history.job_id != job_id:
            raise HTTPException(status_code=403, detail="job_id 与当前面试不一致")
        if request.interview_id is not None and request.interview_id != history.id:
            raise HTTPException(status_code=400, detail="interview_id 与当前进行中的面试不一致")

        position_name = history.position_name
        job_id = history.job_id
        difficulty = history.difficulty
        session_meta = _extract_session_meta(history.chat_context)

        rd = await add_rd(user, db)

        # 传入已有 history 对象，避免内部重复查询
        history = await add_content_history(user, f"候选人：{request.answer}\n", db, history=history)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")

        conversation = history.chat_context
        rag_knowledge = await _get_rag_knowledge(
            request.answer,
            job_id,
            db,
            top_k=3,
        )
        logger.info(f"[RAG] 流式检索完成，知识长度：{len(rag_knowledge)}")
        last_question = _extract_last_ai_question(conversation)
        cc = session_meta.get("candidate_context") or None

        eval_result = await evaluate_answer(
            position_name,
            request.answer,
            last_question,
            rag_context=rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )
        early_end, end_reason, end_suggestions = _early_termination_check(eval_result, rd)
        if early_end:
            closing = (
                f"ai面试官：感谢您参加本次模拟面试。根据当前测评结果，本场面试将提前结束。\n"
                f"【主要原因】{end_reason}\n"
                f"【改进建议】{end_suggestions}\n"
            )
            await add_content_history(user, closing, db)
            completion = await run_interview_completion(user, db)

            async def early_end_stream():
                payload = json.dumps(
                    {
                        "type": "done",
                        "interview_ended": True,
                        "end_reason": end_reason,
                        "end_suggestions": end_suggestions,
                        "answer_analysis": eval_result,
                        "full_text": closing.strip(),
                        "report": completion.get("report"),
                        "message": completion.get("message"),
                    },
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

            return StreamingResponse(
                early_end_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                    "Connection": "keep-alive",
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[文字回答-流式] 预处理失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预处理失败：{e}")

    # --- SSE 生成器（eval_result 已在预处理阶段完成） ---
    async def event_stream():
        full_text = ""
        try:
            async for chunk in generate_interview_question_stream(
                position_name,
                difficulty,
                _conversation_for_llm(conversation),
                rd,
                rag_knowledge,
                interviewer_style=session_meta["interviewer_style"],
                language=session_meta["language"],
                candidate_context=cc,
            ):
                full_text += chunk
                payload = json.dumps({"type": "chunk", "text": chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"

            await add_content_history(user, f"ai面试官：{full_text}\n", db)

            logger.info(f"[文字回答-流式] 完成，问题长度：{len(full_text)}")

            done_payload = json.dumps(
                {
                    "type": "done",
                    "full_text": full_text,
                    "answer_analysis": eval_result,
                    "interview_ended": False,
                },
                ensure_ascii=False,
            )
            yield f"data: {done_payload}\n\n"

        except Exception as e:
            logger.error(f"[文字回答-流式] 流式生成失败：{e}", exc_info=True)
            error_payload = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # 禁用 Nginx 缓冲（部署时需要）
            "Connection": "keep-alive",
        },
    )


# ==================== 提交语音回答 ====================

@router.post("/answer/speech", summary="提交语音回答")
async def submit_speech_answer(
    interview_id: Optional[str] = Form(None),
    job_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传录音文件，后端用 Whisper 识别后生成下一个问题。

    - **file**: 音频文件（webm/wav/mp3）
    - **interview_id**: 面试 ID（表单字段，可选）
    """
    file_size = file.size or 0
    logger.info(f"[语音回答] 用户：{user.username}，文件大小：{file_size} bytes")

    try:
        history = await search_now_history(user, db)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")
        if history.job_id != job_id:
            raise HTTPException(status_code=403, detail="job_id 与当前面试不一致")
        _assert_same_interview(interview_id, history)

        position_name = history.position_name
        job_id = history.job_id
        difficulty = history.difficulty
        session_meta = _extract_session_meta(history.chat_context)

        # 保存临时音频文件（用时间戳防止并发冲突）
        import time as _time
        temp_dir = tempfile.gettempdir()
        # 保留原始格式扩展名（浏览器录制为 webm，不能用 .wav 保存）
        original_ext = os.path.splitext(file.filename or "recording.webm")[1] or ".webm"
        audio_path = os.path.join(
            temp_dir, f"audio_{user.id}_{history.id}_{int(_time.time())}{original_ext}"
        )
        audio_content = await file.read()
        with open(audio_path, "wb") as f:
            f.write(audio_content)
        logger.info(f"[语音回答] 音频已保存：{audio_path}，大小：{len(audio_content)} bytes")

        if len(audio_content) < 512:
            try:
                os.remove(audio_path)
            except Exception:
                pass
            raise HTTPException(status_code=400, detail="录音文件过小，请检查麦克风权限并重新录制")

        # 获取音频时长（PyAV 可解码 webm；wave 模块只能处理标准 WAV）
        audio_duration_sec = 0.0
        try:
            import av as _av
            with _av.open(audio_path) as _container:
                if _container.duration:
                    audio_duration_sec = float(_container.duration) / 1_000_000
        except Exception:
            try:
                import wave
                with wave.open(audio_path, "rb") as wf:
                    audio_duration_sec = wf.getnframes() / wf.getframerate()
            except Exception:
                pass
        logger.info(f"[语音回答] 检测到音频时长：{audio_duration_sec:.1f}s")

        # Whisper 语音识别（全局单例，首次约 5s，后续 < 1s）
        transcription = await speech_to_text(audio_path)
        logger.info(f"[语音回答] 识别结果：{transcription[:80]}")

        # 分析语音特征（语速、停顿词）
        speech_features = analyze_speech_features(transcription, audio_duration_sec)
        logger.info(f"[语音回答] 语速：{speech_features['speech_rate_cpm']} 字/分，停顿词：{speech_features['filler_count']} 个")

        # 清理临时文件
        try:
            os.remove(audio_path)
        except Exception:
            pass

        rd = await add_rd(user, db)

        history = await add_content_history(user, f"候选人（语音）：{transcription}\n", db, history=history)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")

        rag_knowledge = await _get_rag_knowledge(
            transcription,
            job_id,
            db,
            top_k=3,
        )
        last_question = _extract_last_ai_question(history.chat_context)
        cc = session_meta.get("candidate_context") or None

        answer_analysis = await evaluate_answer(
            position_name,
            transcription,
            last_question,
            rag_context=rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )
        early, end_reason, end_suggestions = _early_termination_check(answer_analysis, rd)
        if early:
            closing = (
                f"ai面试官：感谢您参加本次模拟面试。根据当前测评结果，本场语音面试将提前结束。\n"
                f"【主要原因】{end_reason}\n"
                f"【改进建议】{end_suggestions}\n"
            )
            await add_content_history(user, closing, db, history=history)
            completion = await run_interview_completion(user, db)
            return {
                "interview_ended": True,
                "end_reason": end_reason,
                "end_suggestions": end_suggestions,
                "transcription": transcription,
                "speech_features": speech_features,
                "answer_analysis": answer_analysis,
                "report": completion.get("report"),
                "message": completion.get("message"),
            }

        next_question = await generate_interview_question(
            position_name,
            difficulty,
            _conversation_for_llm(history.chat_context),
            rd,
            rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )

        await add_content_history(user, f"ai面试官：{next_question}\n", db, history=history)

        return {
            "transcription": transcription,
            "next_question": next_question,
            "speech_features": speech_features,
            "answer_analysis": answer_analysis,
            "interview_ended": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[语音回答] 系统异常：{type(e).__name__} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理语音回答时发生错误：{e}")


# ==================== 提交视频回答 ====================

@router.post("/answer/video", summary="提交视频回答（含表情分析）")
async def submit_video_answer(
    interview_id: Optional[str] = Form(None),
    job_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传视频文件，进行表情分析 + 语音识别，返回下一个问题。

    - **file**: 视频文件（webm/mp4）
    - **interview_id**: 面试 ID（表单字段，可选）
    """
    file_size = file.size or 0
    logger.info(f"[视频回答] 用户：{user.username}，文件大小：{file_size} bytes")

    try:
        history = await search_now_history(user, db)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")
        if history.job_id != job_id:
            raise HTTPException(status_code=403, detail="job_id 与当前面试不一致")
        _assert_same_interview(interview_id, history)

        position_name = history.position_name
        job_id = history.job_id
        difficulty = history.difficulty
        session_meta = _extract_session_meta(history.chat_context)

        # 用时间戳防止同一用户并发上传时文件路径冲突
        import time as _time
        temp_dir = tempfile.gettempdir()
        ts = int(_time.time())
        video_path = os.path.join(temp_dir, f"video_{user.id}_{history.id}_{ts}.webm")
        video_content = await file.read()
        with open(video_path, "wb") as f:
            f.write(video_content)
        actual_size = len(video_content)
        logger.info(f"[视频回答] 视频已保存：{video_path}，实际大小：{actual_size} bytes")

        if actual_size < 1024:
            logger.warning(f"[视频回答] 视频文件过小（{actual_size} bytes），跳过帧分析")
            try:
                os.remove(video_path)
            except Exception:
                pass
            return {
                "analysis": {}, "next_question": "请重新录制视频，确保录制时长超过2秒",
                "expression": "录制时间过短", "psychology": "", "body_language": "",
                "score": 0, "suggestions": "请保证录制时长至少5秒",
            }

        # 表情分析（DeepSeek 视觉）
        video_analysis = await analyze_video_expression(video_path)

        # 从视频提取音频并识别（需要 FFmpeg）
        audio_path = os.path.join(temp_dir, f"audio_from_video_{user.id}_{history.id}_{ts}.wav")
        transcription = "[视频内容已接收]"
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                 "-ar", "16000", "-ac", "1", audio_path, "-y"],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                transcription = await transcribe_speech(audio_path)
                logger.info(f"[视频回答] 语音识别完成：{transcription[:60]}")
            else:
                logger.warning(f"[视频回答] FFmpeg 音频提取失败（returncode={result.returncode}）")
        except FileNotFoundError:
            logger.warning("[视频回答] 系统未安装 FFmpeg，跳过语音识别（仅做表情分析）")
        except subprocess.TimeoutExpired:
            logger.warning("[视频回答] FFmpeg 超时（>30s），跳过语音识别")
        except Exception as ffmpeg_err:
            logger.error(f"[视频回答] 音频提取异常：{type(ffmpeg_err).__name__}: {ffmpeg_err}")
        finally:
            for p in (video_path, audio_path):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

        full_content = (
            f"候选人（视频）：\n"
            f"表情分析：{video_analysis['expression']}\n"
            f"心理状态：{video_analysis['psychology']}\n"
            f"肢体语言：{video_analysis['body_language']}\n"
            f"回答内容：{transcription}\n"
        )
        rd = await add_rd(user, db)

        history = await add_content_history(user, full_content, db, history=history)
        if not history:
            raise HTTPException(status_code=404, detail="未找到进行中的面试记录")

        rag_knowledge = await _get_rag_knowledge(
            transcription,
            job_id,
            db,
            top_k=1,
        )

        last_question = _extract_last_ai_question(history.chat_context)
        answer_text = transcription if transcription and transcription.strip() else "[视频作答，见上方非语言分析]"
        cc = session_meta.get("candidate_context") or None
        answer_analysis = await evaluate_answer(
            position_name,
            answer_text,
            last_question,
            rag_context=rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )
        early, end_reason, end_suggestions = _early_termination_check(answer_analysis, rd)
        if early:
            closing = (
                f"ai面试官：感谢您参加本次模拟面试。根据当前测评结果，本场视频面试将提前结束。\n"
                f"【主要原因】{end_reason}\n"
                f"【改进建议】{end_suggestions}\n"
            )
            await add_content_history(user, closing, db, history=history)
            completion = await run_interview_completion(user, db)
            return {
                "interview_ended": True,
                "end_reason": end_reason,
                "end_suggestions": end_suggestions,
                "analysis": video_analysis,
                "expression": video_analysis["expression"],
                "psychology": video_analysis["psychology"],
                "body_language": video_analysis["body_language"],
                "score": video_analysis["score"],
                "suggestions": video_analysis["suggestions"],
                "answer_analysis": answer_analysis,
                "report": completion.get("report"),
                "message": completion.get("message"),
            }

        next_question = await generate_interview_question(
            position_name,
            difficulty,
            _conversation_for_llm(history.chat_context),
            rd,
            rag_knowledge,
            interviewer_style=session_meta["interviewer_style"],
            language=session_meta["language"],
            candidate_context=cc,
        )

        await add_content_history(user, f"ai面试官：{next_question}\n", db, history=history)

        return {
            "analysis": video_analysis,
            "next_question": next_question,
            "expression": video_analysis["expression"],
            "psychology": video_analysis["psychology"],
            "body_language": video_analysis["body_language"],
            "score": video_analysis["score"],
            "suggestions": video_analysis["suggestions"],
            "answer_analysis": answer_analysis,
            "interview_ended": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[视频回答] 系统异常：{type(e).__name__} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理视频回答时发生错误：{e}")


# ==================== 实时视频流（分片上传） ====================

@router.post("/answer/video/stream", summary="实时视频流上传（分片）")
async def upload_video_stream(
    interview_id: int = Form(None),
    file: UploadFile = File(...),
    chunk: str = Form("false"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """接收视频流分片并缓冲，当前版本不进行实时分析。"""
    logger.info(f"[视频流] 收到分片，chunk={chunk}，大小：{file.size} bytes")
    return {"success": True, "message": "视频片段接收成功"}


# ==================== 获取面试历史 ====================

@router.get("/history", summary="获取面试历史列表")
async def get_interview_history_endpoint(
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回当前用户的所有面试记录列表"""
    logger.info(f"[面试历史] 用户：{user.username}")

    records = await get_user_history(user, job_id, db)

    difficulty_map = {"entry": "入门级", "intermediate": "进阶级", "expert": "专业级"}

    def _strong_weak(report) -> tuple:
        if not report:
            return [], []
        pairs = []
        fields = [
            ("content_score", "技术知识"),
            ("expression_score", "表达能力"),
            ("logic_score", "逻辑思维"),
            ("communication_score", "沟通表达"),
            ("adaptability_score", "应变能力"),
            ("speech_rate_score", "语速流畅"),
            ("clarity_score", "表达清晰度"),
            ("confidence_score", "自信度"),
        ]
        for attr, label in fields:
            v = getattr(report, attr, None)
            if v is not None:
                try:
                    pairs.append((label, float(v)))
                except (TypeError, ValueError):
                    pass
        pairs.sort(key=lambda x: -x[1])
        if len(pairs) < 2:
            return [x[0] for x in pairs], []
        return [x[0] for x in pairs[:2]], [x[0] for x in pairs[-2:]]

    history_list = []
    for record in records:
        report = await get_evaluation_report_by_id(record.id, db)
        strong, weak = _strong_weak(report)
        history_list.append({
            "id": record.id,
            "job_id": record.job_id,
            "job": record.position_name,
            "level": difficulty_map.get(record.difficulty, record.difficulty),
            "time": str(record.credited_at) if hasattr(record, "credited_at") else "未知时间",
            "status": record.interview_status,
            "mode": record.mode,
            "score": report.total_score if report else None,
            "strong_dims": strong,
            "weak_dims": weak,
        })

    return {"history_list": history_list}


# ==================== 获取面试详情 ====================

@router.get("/detail/{interview_id}", summary="获取面试详情")
async def get_interview_detail_endpoint(
    interview_id: int,
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取指定面试的详细信息，包括评估报告"""
    logger.info(f"[面试详情] ID：{interview_id}")

    history = await get_interview_by_id(interview_id, db)
    if not history:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    if history.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看此面试记录")
    if history.job_id != job_id:
        raise HTTPException(status_code=403, detail="该面试不属于指定岗位")

    report = await get_evaluation_report_by_id(interview_id, db)
    interview_data = build_interview_detail_payload(history, report)
    return {"interview": interview_data}


# ==================== 获取面试统计 ====================

@router.get("/stats", summary="获取面试统计")
async def get_interview_stats(
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回用户各面试模式的真实次数统计"""
    logger.info(f"[面试统计] 用户：{user.username}")

    all_records = await get_user_history(user, job_id, db)

    text_count = sum(1 for r in all_records if getattr(r, "mode", "") == "text")
    speech_count = sum(1 for r in all_records if getattr(r, "mode", "") == "speech")
    video_count = sum(1 for r in all_records if getattr(r, "mode", "") == "video")
    question_count = await search_rd(user, db, job_id=job_id)

    return {
        "text_count": text_count,
        "speech_count": speech_count,
        "video_count": video_count,
        "question_count": question_count,
    }


# ==================== 结束面试，AI 生成报告 ====================

@router.post("/end", summary="结束面试，生成 AI 评估报告")
async def end_interview(
    job_id: int = Query(..., description="岗位ID（必填）"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    结束面试并调用 AI 生成真实的评估报告（非硬编码）。
    """
    history = await search_now_history(user, db)
    if not history:
        raise HTTPException(status_code=404, detail="未找到进行中的面试记录")
    if history.job_id != job_id:
        raise HTTPException(status_code=403, detail="job_id 与当前面试不一致")
    return await run_interview_completion(user, db)


# ==================== 面试上下文预览 ====================

@router.get("/context-preview", summary="面试上下文预览（个人资料与最新简历摘要）")
async def interview_context_preview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """供「开始面试」页展示/编辑默认值。"""
    profile_text, resume_text = await _default_profile_and_resume_text(user, db)
    return {
        "profile_text": profile_text,
        "resume_text": resume_text,
    }


@router.get("/positions", summary="可用岗位列表（仅数据库已入库岗位）")
async def interview_positions(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    result = await db.execute(select(RagJob.id, RagJob.job_name).order_by(RagJob.job_name))
    rows = [{"job_id": int(r[0]), "job_name": str(r[1])} for r in result.all() if r[0] and r[1]]
    return {"status": 200, "positions": rows, "total": len(rows)}


# ==================== 下载面试报告 ====================

@router.get("/download/{interview_id}", summary="下载面试报告（Word 或 PDF）")
async def download_report(
    interview_id: int,
    job_id: int = Query(..., description="岗位ID（必填）"),
    format: str = Query("docx", description="docx 或 pdf"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """下载指定面试的评估报告（Word 或 PDF）"""
    import urllib.parse

    from utils.pdf_export import interview_report_to_pdf

    fmt = (format or "docx").lower()
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="format 仅支持 docx 或 pdf")

    logger.info(f"[下载报告] ID：{interview_id}，格式：{fmt}")

    history = await get_interview_by_id(interview_id, db)
    if not history:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    if history.user_id != user.id:
        if getattr(user, "account_type", "personal") != "enterprise":
            raise HTTPException(status_code=403, detail="无权下载此报告")
        # 企业管理员可下载与企业管理台一致的候选人报告
    if history.job_id != job_id:
        raise HTTPException(status_code=403, detail="该报告不属于指定岗位")

    report = await get_evaluation_report_by_id(interview_id, db)
    if not report:
        raise HTTPException(status_code=404, detail="评估报告不存在，请先结束面试")

    difficulty_label = {"entry": "入门级", "intermediate": "进阶级", "expert": "专业级"}.get(
        history.difficulty, history.difficulty
    )
    mode_label = {"text": "文字面试", "speech": "语音面试", "video": "视频面试"}.get(
        report.mode, report.mode or "未知"
    )

    highlights_list = _deserialize_list(report.highlights)
    weaknesses_list = _deserialize_list(report.weaknesses)
    suggestions_list = _deserialize_list(report.suggestions)

    if fmt == "pdf":
        ds_list = dimension_scores_from_values(
            content_score=float(report.content_score) if report.content_score is not None else None,
            technical_correctness_score=getattr(report, "technical_correctness_score", None),
            knowledge_depth_score=getattr(report, "knowledge_depth_score", None),
            logic_score=getattr(report, "logic_score", None),
            job_match_score=getattr(report, "job_match_score", None),
            communication_score=getattr(report, "communication_score", None),
            adaptability_score=getattr(report, "adaptability_score", None),
            speech_rate_score=getattr(report, "speech_rate_score", None),
            clarity_score=getattr(report, "clarity_score", None),
            confidence_score=getattr(report, "confidence_score", None),
            expression_score=float(report.expression_score) if report.expression_score is not None else None,
            resume_match_score=None,
        )
        dimension_rows = [(d["name"], d["value"]) for d in ds_list]
        buffer = interview_report_to_pdf(
            position_name=history.position_name,
            difficulty_label=difficulty_label,
            mode_label=mode_label,
            interview_round=report.interview_round or 1,
            total_score=float(report.total_score) if report.total_score is not None else 0.0,
            highlights=highlights_list,
            weaknesses=weaknesses_list,
            suggestions=suggestions_list,
            dimension_rows=dimension_rows,
            improvement_resources=_safe_improvement_resources(
                getattr(report, "improvement_resources_json", None)
            ),
        )
        filename = f"面试报告_{history.position_name}_{interview_id}.pdf"
        media = "application/pdf"
    else:
        buffer = _generate_report_docx(
            history=history,
            report=report,
            difficulty_label=difficulty_label,
            mode_label=mode_label,
            highlights_list=highlights_list,
            weaknesses_list=weaknesses_list,
            suggestions_list=suggestions_list,
        )
        filename = f"面试报告_{history.position_name}_{interview_id}.docx"
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    encoded_filename = urllib.parse.quote(filename)

    return StreamingResponse(
        buffer,
        media_type=media,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        },
    )


def _generate_report_docx(
    history,
    report,
    difficulty_label: str,
    mode_label: str,
    highlights_list: list,
    weaknesses_list: list,
    suggestions_list: list,
):
    """生成面试报告 Word 文档，返回 BytesIO"""
    import io
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    FONT_CN = "微软雅黑"

    def _set_run_font(run, font_name: str = FONT_CN):
        # 同时设置 ascii / eastAsia，避免中文落到默认英文字体
        run.font.name = font_name
        r = run._element
        r_pr = r.get_or_add_rPr()
        r_fonts = r_pr.find(qn("w:rFonts"))
        if r_fonts is None:
            r_fonts = OxmlElement("w:rFonts")
            r_pr.insert(0, r_fonts)
        r_fonts.set(qn("w:ascii"), font_name)
        r_fonts.set(qn("w:hAnsi"), font_name)
        r_fonts.set(qn("w:eastAsia"), font_name)

    def _fmt_para(p, space_after_pt=6, line_multiple=1.2):
        pf = p.paragraph_format
        pf.space_after = Pt(space_after_pt)
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = line_multiple
        return p

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    def add_heading(text, level=1, color=(0x2C, 0x3E, 0x50), size=14):
        p = doc.add_paragraph()
        _fmt_para(p, space_after_pt=8 if level == 1 else 6, line_multiple=1.0)
        run = p.add_run(text)
        _set_run_font(run)
        run.bold = True
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(*color)
        if level == 1:
            pPr = p._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '6')
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), '409EFF')
            pBdr.append(bottom)
            pPr.append(pBdr)
        return p

    def add_kv(label, value, label_bold=True):
        p = doc.add_paragraph()
        _fmt_para(p, space_after_pt=3, line_multiple=1.2)
        r1 = p.add_run(f"{label}：")
        _set_run_font(r1)
        r1.bold = label_bold
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = RGBColor(0x60, 0x62, 0x66)
        r2 = p.add_run(str(value))
        _set_run_font(r2)
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = RGBColor(0x30, 0x31, 0x33)

    def add_score_row(label, score, max_score=10):
        p = doc.add_paragraph()
        _fmt_para(p, space_after_pt=2, line_multiple=1.15)
        r1 = p.add_run(f"  {label}：")
        _set_run_font(r1)
        r1.font.size = Pt(10.5)
        r1.font.color.rgb = RGBColor(0x60, 0x62, 0x66)
        score_val = float(score) if score is not None else 0.0
        r2 = p.add_run(f"{score_val:.1f} / {max_score}")
        _set_run_font(r2)
        r2.bold = True
        r2.font.size = Pt(11)
        if score_val >= 8.5:
            r2.font.color.rgb = RGBColor(0x67, 0xC2, 0x3A)
        elif score_val >= 7.0:
            r2.font.color.rgb = RGBColor(0x40, 0x9E, 0xFF)
        elif score_val >= 5.0:
            r2.font.color.rgb = RGBColor(0xE6, 0xA2, 0x3C)
        else:
            r2.font.color.rgb = RGBColor(0xF5, 0x6C, 0x6C)

    def add_bullet_list(items, color=(0x55, 0x55, 0x55)):
        if not items:
            p = doc.add_paragraph("  暂无")
            _fmt_para(p, space_after_pt=6, line_multiple=1.2)
            for r in p.runs:
                _set_run_font(r)
                r.font.size = Pt(10.5)
                r.font.color.rgb = RGBColor(0xC0, 0xC4, 0xCC)
            return
        for item in items:
            # 不使用 List Bullet（不同系统字体/缩进差异大），统一为手动 bullet
            p = doc.add_paragraph()
            _fmt_para(p, space_after_pt=4, line_multiple=1.25)
            run = p.add_run(f"•  {str(item).strip()}")
            _set_run_font(run)
            run.font.size = Pt(10.5)
            run.font.color.rgb = RGBColor(*color)

    # ─── 标题 ─────────────────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fmt_para(title_para, space_after_pt=3, line_multiple=1.0)
    title_run = title_para.add_run("AI 模拟面试评估报告")
    _set_run_font(title_run)
    title_run.bold = True
    title_run.font.size = Pt(22)
    title_run.font.color.rgb = RGBColor(0x30, 0x31, 0x33)

    subtitle_para = doc.add_paragraph()
    subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fmt_para(subtitle_para, space_after_pt=12, line_multiple=1.05)
    subtitle_run = subtitle_para.add_run(f"岗位：{history.position_name}  |  难度：{difficulty_label}  |  形式：{mode_label}")
    _set_run_font(subtitle_run)
    subtitle_run.font.size = Pt(11)
    subtitle_run.font.color.rgb = RGBColor(0x90, 0x93, 0x99)

    doc.add_paragraph()

    # ─── 基本信息 ─────────────────────────────────────────
    add_heading("基本信息", level=1, color=(0x40, 0x9E, 0xFF), size=13)
    add_kv("应聘岗位", history.position_name)
    add_kv("面试难度", difficulty_label)
    add_kv("面试形式", mode_label)
    add_kv("面试轮次", f"共 {report.interview_round} 轮")
    doc.add_paragraph()

    # ─── 综合评分 ─────────────────────────────────────────
    add_heading("综合评分", level=1, color=(0x40, 0x9E, 0xFF), size=13)
    total = float(report.total_score) if report.total_score is not None else 0.0
    p = doc.add_paragraph()
    _fmt_para(p, space_after_pt=8, line_multiple=1.1)
    r = p.add_run(f"综合得分：{total:.1f} / 10")
    _set_run_font(r)
    r.bold = True
    r.font.size = Pt(14)
    if total >= 8.5:
        r.font.color.rgb = RGBColor(0x67, 0xC2, 0x3A)
    elif total >= 7.0:
        r.font.color.rgb = RGBColor(0x40, 0x9E, 0xFF)
    elif total >= 5.0:
        r.font.color.rgb = RGBColor(0xE6, 0xA2, 0x3C)
    else:
        r.font.color.rgb = RGBColor(0xF5, 0x6C, 0x6C)
    doc.add_paragraph()

    # ─── 各维度得分 ───────────────────────────────────────
    add_heading("各维度得分", level=1, color=(0x40, 0x9E, 0xFF), size=13)

    ds_docx = dimension_scores_from_values(
        content_score=float(report.content_score) if report.content_score is not None else None,
        technical_correctness_score=getattr(report, "technical_correctness_score", None),
        knowledge_depth_score=getattr(report, "knowledge_depth_score", None),
        logic_score=getattr(report, "logic_score", None),
        job_match_score=getattr(report, "job_match_score", None),
        communication_score=getattr(report, "communication_score", None),
        adaptability_score=getattr(report, "adaptability_score", None),
        speech_rate_score=getattr(report, "speech_rate_score", None),
        clarity_score=getattr(report, "clarity_score", None),
        confidence_score=getattr(report, "confidence_score", None),
        expression_score=float(report.expression_score) if report.expression_score is not None else None,
        resume_match_score=None,
    )
    for row in ds_docx:
        add_score_row(row["name"], row["value"])
    doc.add_paragraph()

    # ─── 亮点 ─────────────────────────────────────────────
    add_heading("亮点表现", level=1, color=(0x67, 0xC2, 0x3A), size=13)
    add_bullet_list(highlights_list, color=(0x52, 0xC4, 0x1A))
    doc.add_paragraph()

    # ─── 不足 ─────────────────────────────────────────────
    add_heading("不足之处", level=1, color=(0xE6, 0xA2, 0x3C), size=13)
    add_bullet_list(weaknesses_list, color=(0xB4, 0x5A, 0x00))
    doc.add_paragraph()

    # ─── 改进建议 ─────────────────────────────────────────
    add_heading("改进建议", level=1, color=(0x40, 0x9E, 0xFF), size=13)
    add_bullet_list(suggestions_list, color=(0x30, 0x6F, 0xBF))
    doc.add_paragraph()

    ir_docx = _safe_improvement_resources(getattr(report, "improvement_resources_json", None))
    if ir_docx:
        kp = ir_docx.get("knowledge_points") or []
        if isinstance(kp, list) and kp:
            add_heading("巩固知识点", level=1, color=(0x0D, 0x94, 0x88), size=13)
            lines = []
            for it in kp[:10]:
                if isinstance(it, dict):
                    lines.append(
                        f"{it.get('topic', '')}：{it.get('summary', '')}（行动：{it.get('action', '')}）"
                    )
            add_bullet_list(lines, color=(0x11, 0x5E, 0x59))
            doc.add_paragraph()
        siq = ir_docx.get("sample_interview_questions") or []
        if isinstance(siq, list) and siq:
            add_heading("推荐练习面试题", level=1, color=(0x7C, 0x3A, 0xED), size=13)
            lines = []
            for it in siq[:10]:
                if isinstance(it, dict):
                    lines.append(f"{it.get('question', '')} — 考察：{it.get('focus', '')}")
            add_bullet_list(lines, color=(0x55, 0x1F, 0x99))
            doc.add_paragraph()
        cr = ir_docx.get("communication_readings") or []
        if isinstance(cr, list) and cr:
            add_heading("沟通与表达延伸阅读", level=1, color=(0x03, 0x69, 0xA1), size=13)
            lines = []
            for it in cr[:8]:
                if isinstance(it, dict):
                    u = it.get("url_or_search") or it.get("url") or ""
                    lines.append(f"{it.get('title', '')}：{it.get('summary', '')}（{u}）")
            add_bullet_list(lines, color=(0x0C, 0x4A, 0x6E))
            doc.add_paragraph()

    # ─── 问答记录 ─────────────────────────────────────────
    if history.chat_context:
        lines = [l for l in history.chat_context.strip().split("\n") if l.strip()]
        if lines and lines[0].startswith("[SESSION_META]"):
            lines = lines[1:]
        qa_pairs = []
        for i in range(0, len(lines) - 1, 2):
            if i + 1 < len(lines):
                q_line = lines[i]
                if not (q_line.startswith("ai面试官：") or q_line.startswith("面试官：")):
                    continue
                raw_answer = lines[i + 1]
                j = i + 2
                while j < len(lines) and not lines[j].startswith("ai面试官：") and not lines[j].startswith("面试官："):
                    raw_answer += " " + lines[j]
                    j += 1
                qa_pairs.append({
                    "q": q_line.replace("ai面试官：", "").replace("面试官：", "").strip(),
                    "a": raw_answer
                        .replace("候选人：", "").replace("候选人（语音）：", "").replace("候选人（视频）：", "")
                        .replace("表情分析：", "[表情] ").replace("心理状态：", "[状态] ")
                        .replace("肢体语言：", "[肢体] ").replace("回答内容：", "")
                        .strip(),
                })
        if qa_pairs:
            add_heading("问答记录", level=1, color=(0x60, 0x62, 0x66), size=13)
            for idx, qa in enumerate(qa_pairs, 1):
                p = doc.add_paragraph()
                r = p.add_run(f"Q{idx}：{qa['q']}")
                _set_run_font(r)
                r.bold = True
                r.font.size = Pt(10.5)
                r.font.color.rgb = RGBColor(0x40, 0x9E, 0xFF)

                a_p = doc.add_paragraph()
                a_r = a_p.add_run(f"A：{qa['a'] or '（未作答）'}")
                _set_run_font(a_r)
                a_r.font.size = Pt(10.5)
                a_r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
                doc.add_paragraph()

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ==================== 能力提升反馈 ====================

@router.get("/growth-curve", summary="成长曲线（ECharts 标准结构）")
async def get_growth_curve(
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await get_user_history(user, job_id, db)
    rows = sorted(rows, key=lambda x: getattr(x, "credited_at", None) or getattr(x, "id", 0))
    x_axis: list[str] = []
    dim_map = {
        "专业知识": [],
        "逻辑思维": [],
        "表达能力": [],
        "综合得分": [],
    }
    for r in rows:
        rep = await get_evaluation_report_by_id(r.id, db)
        if not rep:
            continue
        x_axis.append(str(getattr(r, "credited_at", "") or r.id))
        dim_map["专业知识"].append(float(rep.content_score or 0) * 10)
        dim_map["逻辑思维"].append(float(rep.logic_score or 0) * 10)
        dim_map["表达能力"].append(float(rep.expression_score or 0) * 10)
        dim_map["综合得分"].append(float(rep.total_score or 0) * 10)
    series = [{"name": k, "data": v} for k, v in dim_map.items()]
    return {"job_id": job_id, "xAxis": x_axis, "series": series}


@router.get("/growth-advice", summary="获取个性化能力提升建议")
async def get_growth_advice(
    job_id: int = Query(..., description="岗位ID（必填）"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    根据用户历史面试评估数据，用 AI 生成个性化提升建议、练习计划和技术学习路线。
    """
    from config.llm_conf import PROMPT_GROWTH_ADVICE, MODEL_REPORT, call_llm
    import time as _time

    t0 = _time.perf_counter()
    max_samples = env_int("GROWTH_ADVICE_MAX_SAMPLES", 24)
    llm_timeout_main = env_int("GROWTH_ADVICE_LLM_TIMEOUT", 45)
    llm_timeout_retry = env_int("GROWTH_ADVICE_LLM_RETRY_TIMEOUT", 25)

    # 获取该用户全部历史评估记录
    history_list = await get_user_history(user, job_id, db)
    completed = [h for h in history_list if h.interview_status == "面试结束"]

    if not completed:
        return {
            "has_data": False,
            "interview_count": 0,
            "positions": [],
            "trend_desc": "",
            "advice": {
                "overall_advice": "",
                "weak_points": [],
                "improvement_plan": [],
                "learning_roadmap": {"total_weeks": 0, "phases": []},
                "practice_suggestions": [],
                "learning_resources": [],
            },
            "knowledge_map": {"nodes": [], "edges": []},
            "ability_analysis": {"dimension_avg": {}, "overall_trend": "", "sample_size": 0},
        }

    target = completed
    # 样本过大时仅取最近若干次，避免长等待
    target = sorted(
        target,
        key=lambda x: getattr(x, "credited_at", None) or getattr(x, "id", 0),
        reverse=True,
    )[:max_samples]

    # 统计各维度平均分
    dim_scores: dict = {
        "技术知识": [],
        "技术正确性": [],
        "知识深度": [],
        "岗位匹配": [],
        "逻辑思维": [],
        "沟通表达": [],
        "应变能力": [],
        "表达能力": [],
        "语速流畅": [],
        "表达清晰度": [],
        "自信度": [],
    }
    overall_scores = []
    highlights_all = []
    weaknesses_all = []
    job_names = set()

    for h in target:
        if h.position_name:
            job_names.add(h.position_name)
        # 获取关联的评估报告
        report = await get_evaluation_report_by_id(h.id, db)
        if not report:
            continue
        if report.total_score is not None:
            overall_scores.append(report.total_score)
        # 维度分
        field_map = {
            "技术知识": report.content_score,
            "技术正确性": getattr(report, "technical_correctness_score", None),
            "知识深度": getattr(report, "knowledge_depth_score", None),
            "岗位匹配": getattr(report, "job_match_score", None),
            "逻辑思维": report.logic_score,
            "沟通表达": report.communication_score,
            "应变能力": report.adaptability_score,
            "表达能力": report.expression_score,
            "语速流畅": report.speech_rate_score,
            "表达清晰度": report.clarity_score,
            "自信度": report.confidence_score,
        }
        for dim, val in field_map.items():
            if val is not None:
                dim_scores[dim].append(float(val))
        if report.highlights:
            h_list = _deserialize_list(report.highlights)
            highlights_all.extend(h_list[:2] if h_list else [])
        if report.weaknesses:
            w_list = _deserialize_list(report.weaknesses)
            weaknesses_all.extend(w_list[:2] if w_list else [])

    # 计算各维度平均
    dim_avg = {k: (sum(v) / len(v)) for k, v in dim_scores.items() if v}
    dim_summary = "\n".join(
        [f"- {k}：{v:.1f}/10" for k, v in sorted(dim_avg.items(), key=lambda x: x[1])]
    ) or "（暂无维度数据）"

    # 成长趋势描述
    if len(overall_scores) >= 2:
        trend = overall_scores[-1] - overall_scores[0]
        trend_desc = f"从 {overall_scores[0]:.1f} 上升到 {overall_scores[-1]:.1f}（+{trend:.1f}）" if trend > 0 \
            else f"从 {overall_scores[0]:.1f} 下降到 {overall_scores[-1]:.1f}（{trend:.1f}）" if trend < 0 \
            else f"保持稳定在 {overall_scores[-1]:.1f}"
    elif overall_scores:
        trend_desc = f"当前分数：{overall_scores[-1]:.1f}"
    else:
        trend_desc = "暂无分数数据"

    job_row = await _require_job_by_id(db, job_id)
    infer_position = job_row.job_name
    highlights_str = "；".join(highlights_all[:4]) if highlights_all else "暂无"
    weaknesses_str = "；".join(weaknesses_all[:4]) if weaknesses_all else "暂无"

    lookup_job = infer_position
    job_tech_block = "（未匹配 job 表，请上传带岗位的题库知识文档）"
    question_bank_excerpt = "（暂无结构化题目，请先入库题库）"
    kb_excerpt = "（向量检索暂不可用或无命中）"
    if lookup_job:
        from models.rag_schema import Job as SchemaJob, Question as SchemaQuestion

        jres = await db.execute(select(SchemaJob).where(SchemaJob.job_name == lookup_job))
        job_row = jres.scalar_one_or_none()
        if not job_row:
            jres = await db.execute(select(SchemaJob).where(SchemaJob.job_name.contains(lookup_job)).limit(1))
            job_row = jres.scalar_one_or_none()
        if job_row:
            ts = job_row.tech_stack
            if isinstance(ts, list):
                job_tech_block = "、".join(str(x) for x in ts[:40]) or job_tech_block
            elif isinstance(ts, dict):
                job_tech_block = "、".join(str(v) for v in ts.values())[:2000] or job_tech_block
            else:
                job_tech_block = str(ts or job_tech_block)[:2000]
            qres = await db.execute(
                select(SchemaQuestion)
                .where(SchemaQuestion.job_id == job_row.id)
                .order_by(SchemaQuestion.id.desc())
                .limit(16)
            )
            qlines = []
            for q in qres.scalars().all():
                ep = (q.exam_points or q.category or "").strip()
                qlines.append(f"- 【{ep}】{q.content[:280]}")
            if qlines:
                question_bank_excerpt = "\n".join(qlines)[:8000]
    rag_for_growth = await retrieve_context(
        db=db,
        query=f"{infer_position} {weaknesses_str[:500]}".strip(),
        filter_data={"job_id": str(job_id)},
    )
    parts = []
    for h in (rag_for_growth.get("chunks") or [])[:6]:
        parts.append(f"「知识点」{str(h.get('content') or '')[:520]}")
    if parts:
        kb_excerpt = "\n---\n".join(parts)[:8000]

    prompt = PROMPT_GROWTH_ADVICE.format(
        position=infer_position,
        interview_count=len(target),
        dimension_summary=dim_summary,
        trend_desc=trend_desc,
        highlights=highlights_str,
        weaknesses=weaknesses_str,
        job_tech_block=job_tech_block[:3000],
        question_bank_excerpt=question_bank_excerpt[:2600],
        kb_excerpt=kb_excerpt[:2600],
    )

    raw = await asyncio.wait_for(
        call_llm(prompt=prompt, model=MODEL_REPORT),
        timeout=llm_timeout_main,
    )
    try:
        advice = parse_llm_json_object(raw)
    except json.JSONDecodeError as e:
        pos = getattr(e, "pos", None)
        snippet = (raw or "")[:900]
        logger.error(
            "[成长建议] LLM JSON 解析失败: %s pos=%s 原文片段=%r",
            e,
            pos,
            snippet,
        )
        raise HTTPException(
            status_code=502,
            detail="AI 返回的成长建议格式异常，请稍后重试。若持续出现请联系管理员。",
        ) from e
    required_advice_keys = [
        "overall_advice",
        "weak_points",
        "improvement_plan",
        "learning_roadmap",
        "practice_suggestions",
        "learning_resources",
    ]
    for key in required_advice_keys:
        if key not in advice:
            raise HTTPException(status_code=500, detail=f"成长建议结构错误，缺少字段: {key}")

    for opt_key in ("deep_dive_knowledge", "star_interview_questions", "communication_readings"):
        if opt_key not in advice or not isinstance(advice.get(opt_key), list):
            advice[opt_key] = []

    if isinstance(advice, dict):
        from utils.learning_resources import ensure_knowledge_graph, merge_learning_resources

        merge_learning_resources(advice, weaknesses_str, infer_position)
        ensure_knowledge_graph(advice)

    from utils.knowledge_map import build_job_knowledge_map
    km_data = await asyncio.wait_for(
        build_job_knowledge_map(db, user, infer_position, query_hint=weaknesses_str[:400]),
        timeout=10,
    )
    logger.info(
        "[成长建议] 完成 user=%s samples=%s elapsed=%.2fs",
        user.id,
        len(target),
        _time.perf_counter() - t0,
    )

    return {
        "has_data": True,
        "interview_count": len(target),
        "positions": list(job_names),
        "trend_desc": trend_desc,
        "advice": advice,
        "knowledge_map": km_data,
        "ability_analysis": {
            "dimension_avg": dim_avg,
            "overall_trend": trend_desc,
            "sample_size": len(target),
        },
    }


# ==================== 讯飞虚拟人（服务端代理）====================

@router.get("/virtual-human/config", summary="讯飞虚拟人：配置与是否可用")
async def virtual_human_config(user: User = Depends(get_current_user)):
    from services import iflytek_virtual_human as vh

    ok = vh.is_iflytek_virtual_human_configured()
    sdk_ok = vh.is_iflytek_websdk_configured()
    missing_fields = []
    if not vh.IFLYTEK_APP_ID:
        missing_fields.append("IFLYTEK_APP_ID")
    if not vh.IFLYTEK_API_KEY:
        missing_fields.append("IFLYTEK_API_KEY")
    if not vh.IFLYTEK_API_SECRET:
        missing_fields.append("IFLYTEK_API_SECRET")
    if not vh.IFLYTEK_VH_SCENE_ID:
        missing_fields.append("IFLYTEK_VH_SCENE_ID")
    if not vh.IFLYTEK_VH_INTERACT_SERVER_URL:
        missing_fields.append("IFLYTEK_VH_INTERACT_SERVER_URL")
    scene_id = (vh.IFLYTEK_VH_SCENE_ID or "").strip()
    config_hints = []
    if scene_id.isdigit() and len(scene_id) < 15:
        config_hints.append(
            "IFLYTEK_VH_SCENE_ID 过短：交互 WebSDK 一般应填服务编排页的「接口服务ID」（长数字，多 15～19 位），不是 1、2 等占位。"
        )

    return {
        "enabled": ok,
        "sdk_ready": sdk_ok,
        "missing_fields": missing_fields,
        "config_hints": config_hints,
        "app_id": vh.IFLYTEK_APP_ID if ok else None,
        "api_key": vh.IFLYTEK_API_KEY if ok else None,
        "api_secret": vh.IFLYTEK_API_SECRET if ok else None,
        "scene_id": vh.IFLYTEK_VH_SCENE_ID if ok else None,
        "interact_server_url": vh.IFLYTEK_VH_INTERACT_SERVER_URL if ok else None,
        "avatar_id": vh.IFLYTEK_VH_AVATAR_ID,
        "vh_width": vh.IFLYTEK_VH_WIDTH,
        "vh_height": vh.IFLYTEK_VH_HEIGHT,
        "stream_protocol": vh.IFLYTEK_VH_PROTOCOL,
        "tts_vcn": vh.IFLYTEK_VH_TTS_VCN,
        "tts_aue": vh.IFLYTEK_VH_TTS_AUE,
        "audio_encoding": vh.IFLYTEK_VH_TTS_AUDIO_ENCODING,
        "bg_res_key": vh.IFLYTEK_VH_BG_RES_KEY,
        "sync_mode": vh.IFLYTEK_VH_SYNC_MODE,
        "has_audio": vh.IFLYTEK_VH_HAS_AUDIO,
        "video_type": vh.IFLYTEK_VH_VIDEO_TYPE,
        "hint": "浏览器只能播放 HTTP-FLV；若返回 RTMP 地址，请在前端按同路径转换为 .flv 直连播放，并确保源站开启 CORS。",
    }


@router.post("/virtual-human/start", summary="讯飞虚拟人：建立会话")
async def virtual_human_start(user: User = Depends(get_current_user)):
    from services import iflytek_virtual_human as vh

    if not vh.is_iflytek_virtual_human_configured():
        raise HTTPException(status_code=503, detail="未配置 IFLYTEK_*，请在 backend/.env 中填写")
    try:
        data = await vh.vms_start(user.id)
        return data
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/virtual-human/speak", summary="讯飞虚拟人：文本驱动播报")
async def virtual_human_speak(text: str = Form(...), user: User = Depends(get_current_user)):
    from services import iflytek_virtual_human as vh

    if not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    try:
        return await vh.vms_text_drive(user.id, text.strip())
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/virtual-human/stop", summary="讯飞虚拟人：结束会话")
async def virtual_human_stop(user: User = Depends(get_current_user)):
    from services import iflytek_virtual_human as vh

    await vh.vms_stop(user.id)
    return {"ok": True}
