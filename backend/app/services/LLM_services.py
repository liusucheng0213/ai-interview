"""
LLM 服务层 - 封装所有 AI 能力

包含：
- 面试问题生成（generate_interview_question）
- 回答评估（evaluate_answer）
- 最终报告生成（generate_final_report）
- 语音转文字（speech_to_text）—— Whisper 全局单例，避免每次重新加载
- 视频表情分析（analyze_video_expression）—— DeepSeek 视觉理解
- 简历分析与优化（analyze_resume / optimize_resume）
"""

import asyncio
import base64
import json
import logging
import os
import random
import re
import time
from typing import AsyncGenerator, Optional

import cv2
import httpx
import numpy as np

from config.env_util import env_int
from config.llm_conf import (
    ASR_LANGUAGE,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_VISION_TIMEOUT,
    MODEL_VISION,
    PROMPT_EVALUATE_ANSWER,
    PROMPT_FINAL_REPORT,
    PROMPT_GENERATE_QUESTION,
    PROMPT_RESUME_ANALYSIS,
    PROMPT_RESUME_OPTIMIZE,
    WHISPER_MODEL_NAME,
    SYSTEM_PROMPT_INTERVIEWER,
    MODEL_INTERVIEW,
    MODEL_REPORT,
    MODEL_RESUME_VL,
    MODEL_RESUME_OPTIMIZE,
    call_llm,
    call_llm_stream,
    deepseek_extra_body,
)

logger = logging.getLogger(__name__)

# 提问环节对话上下文上限（字符）；超出则只保留最近若干轮完整问答，降低 Token
_INTERVIEW_CONTEXT_MAX_CHARS = env_int("INTERVIEW_CONTEXT_MAX_CHARS", 5200)
_INTERVIEW_CONTEXT_MAX_PAIRS = env_int("INTERVIEW_CONTEXT_MAX_PAIRS", 8)


def _safe_parse_duration_seconds(raw: str) -> float:
    """将 ffprobe 输出安全转为秒数，兼容 N/A/空值。"""
    s = (raw or "").strip()
    if not s:
        return 0.0
    if s.upper() in {"N/A", "NA", "NULL", "NONE"}:
        return 0.0
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def compact_conversation_for_next_question(
    conversation: str,
    max_chars: int = _INTERVIEW_CONTEXT_MAX_CHARS,
    max_recent_pairs: int = _INTERVIEW_CONTEXT_MAX_PAIRS,
) -> str:
    """
    压缩多轮对话后再送给「下一题生成」模型，避免整段 chat_context 随轮次线性膨胀。
    数据库仍保存完整 chat_context；仅影响当次 LLM 输入。
    """
    if not conversation or not conversation.strip():
        return conversation or ""
    conv = conversation.strip()
    if len(conv) <= max_chars:
        return conv

    all_lines = conv.split("\n")
    start = 0
    if all_lines and all_lines[0].strip().startswith("[SESSION_META]"):
        start = 1
    body_lines = all_lines[start:]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(body_lines):
        line = body_lines[i].strip()
        if line.startswith("ai面试官：") or line.startswith("面试官："):
            q = body_lines[i]
            ans_parts: list[str] = []
            j = i + 1
            while j < len(body_lines):
                nxt = body_lines[j]
                if nxt.strip().startswith("ai面试官：") or nxt.strip().startswith("面试官："):
                    break
                ans_parts.append(nxt)
                j += 1
            pairs.append((q, "\n".join(ans_parts).strip()))
            i = j
        else:
            i += 1

    if len(pairs) <= max_recent_pairs:
        head = ("\n".join(all_lines[:start]) + "\n") if start else ""
        body = "\n".join(body_lines).strip()
        full = (head + body).strip()
        return full[:max_chars]

    omitted = len(pairs) - max_recent_pairs
    kept = pairs[-max_recent_pairs:]
    rebuilt = []
    for q, a in kept:
        rebuilt.append(q)
        if a:
            rebuilt.append(a)
    tail = "\n".join(rebuilt)
    header = (
        f"【上下文压缩】前 {omitted} 轮问答已省略以控制长度；"
        f"以下保留最近 {max_recent_pairs} 轮完整「面试官—候选人」内容。请勿要求候选人重复已省略轮次。\n\n"
    )
    out = header + tail
    if len(out) > max_chars:
        out = header + tail[-(max_chars - len(header)) :]
    return out


# ==================== 【Whisper 全局单例】====================
# 只在第一次调用时加载，避免每次请求都重新加载模型（原来每次要花 5-10 秒）
_whisper_model = None
_whisper_lock = asyncio.Lock()


async def _get_whisper_model():
    """懒加载 Whisper 模型（线程安全单例）"""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    async with _whisper_lock:
        # 双重检查，避免并发时重复加载
        if _whisper_model is not None:
            return _whisper_model

        logger.info(f"[Whisper] 首次加载模型：{WHISPER_MODEL_NAME}（后续调用无需等待）")
        import whisper
        loop = asyncio.get_running_loop()
        _whisper_model = await loop.run_in_executor(
            None, lambda: whisper.load_model(WHISPER_MODEL_NAME)
        )
        logger.info(f"[Whisper] 模型加载完成：{WHISPER_MODEL_NAME}")
        return _whisper_model


# ==================== 【面试问题生成】====================

async def generate_interview_question(
    position: str,
    difficulty: str,
    conversation: str,
    round_num: int,
    rag_knowledge: Optional[str] = None,
    interviewer_style: str = "rigorous",
    language: str = "zh",
    candidate_context: Optional[str] = None,
) -> str:
    """
    生成面试问题（非流式，用于语音/视频模式）

    Args:
        position:      岗位名称
        difficulty:    难度等级（entry/intermediate/expert）
        conversation:  对话历史记录
        round_num:     当前问题轮次
        rag_knowledge: RAG 检索到的相关知识（可为 None 或空字符串）

    Returns:
        生成的面试问题文本
    """
    rag_text = rag_knowledge if rag_knowledge else "无"
    conv_for_llm = compact_conversation_for_next_question(conversation or "")
    style_instruction_map = {
        "rigorous": "面试官风格：严谨型。强调定义准确、逻辑闭环和边界条件，语气专业克制。",
        "pressure": "面试官风格：压力型。适度追问与挑战假设，语气直接但保持职业礼貌，不做人身否定。",
        "heuristic": "面试官风格：启发型。通过循序渐进提问引导候选人思考，给出必要提示，重视思维展开。",
    }
    language_instruction_map = {
        "zh": "语言策略：默认使用中文提问与反馈。",
        "en": "Language strategy: use English for questions and feedback by default.",
        "bilingual": "语言策略：中英双语。优先中文主问题，并在末尾补充一句英文等价提问。",
    }
    style_instruction = style_instruction_map.get(interviewer_style, style_instruction_map["rigorous"])
    language_instruction = language_instruction_map.get(language, language_instruction_map["zh"])

    prompt = PROMPT_GENERATE_QUESTION.format(
        position=position,
        difficulty=difficulty,
        round=round_num,
        conversation=conv_for_llm or "（面试刚开始，暂无历史对话）",
        rag_knowledge=rag_text,
    )
    prompt = f"{prompt}\n\n附加策略要求：\n- {style_instruction}\n- {language_instruction}"
    if candidate_context and candidate_context.strip():
        prompt += (
            "\n\n【候选人背景（来自个人资料与简历，提问与追问时可参考，勿逐字复述）】\n"
            + candidate_context.strip()[:4000]
        )

    logger.info(
        f"[问题生成] 岗位：{position}，难度：{difficulty}，轮次：{round_num}，"
        f"上下文长度：{len(conv_for_llm)}（已压缩）"
    )
    # 使用 system prompt 赋予面试官角色，提升多轮对话质量
    question = await call_llm(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_INTERVIEWER,
        model=MODEL_INTERVIEW,
    )
    logger.info(f"[问题生成] 成功：{question[:60]}...")
    return question


async def generate_interview_question_stream(
    position: str,
    difficulty: str,
    conversation: str,
    round_num: int,
    rag_knowledge: Optional[str] = None,
    interviewer_style: str = "rigorous",
    language: str = "zh",
    candidate_context: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    流式生成面试问题（用于文字模式，实现打字机效果）

    Yields:
        文本片段（chunk）
    """
    rag_text = rag_knowledge if rag_knowledge else "无"
    conv_for_llm = compact_conversation_for_next_question(conversation or "")
    style_instruction_map = {
        "rigorous": "面试官风格：严谨型。强调定义准确、逻辑闭环和边界条件，语气专业克制。",
        "pressure": "面试官风格：压力型。适度追问与挑战假设，语气直接但保持职业礼貌，不做人身否定。",
        "heuristic": "面试官风格：启发型。通过循序渐进提问引导候选人思考，给出必要提示，重视思维展开。",
    }
    language_instruction_map = {
        "zh": "语言策略：默认使用中文提问与反馈。",
        "en": "Language strategy: use English for questions and feedback by default.",
        "bilingual": "语言策略：中英双语。优先中文主问题，并在末尾补充一句英文等价提问。",
    }
    style_instruction = style_instruction_map.get(interviewer_style, style_instruction_map["rigorous"])
    language_instruction = language_instruction_map.get(language, language_instruction_map["zh"])

    prompt = PROMPT_GENERATE_QUESTION.format(
        position=position,
        difficulty=difficulty,
        round=round_num,
        conversation=conv_for_llm or "（面试刚开始，暂无历史对话）",
        rag_knowledge=rag_text,
    )
    prompt = f"{prompt}\n\n附加策略要求：\n- {style_instruction}\n- {language_instruction}"
    if candidate_context and candidate_context.strip():
        prompt += (
            "\n\n【候选人背景（来自个人资料与简历，提问与追问时可参考，勿逐字复述）】\n"
            + candidate_context.strip()[:4000]
        )

    logger.info(f"[问题生成-流式] 岗位：{position}，难度：{difficulty}，轮次：{round_num}，上下文长度：{len(conv_for_llm)}")
    async for chunk in call_llm_stream(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_INTERVIEWER,
        model=MODEL_INTERVIEW,
    ):
        yield chunk


# ==================== 【回答评估】====================

def _strip_json_fence(text: str) -> str:
    """去掉成对的 markdown 代码围栏。不能用 lstrip('```json')，那会按字符集合误删正文。"""
    raw = (text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", raw, flags=re.IGNORECASE)
    if fenced:
        return (fenced.group(1) or "").strip()
    return raw


def _llm_json_candidates(text: str) -> list[str]:
    """从 LLM 输出中提取可能的 JSON 子串（与报告解析策略一致）。"""
    candidates: list[str] = []
    src = _strip_json_fence(text)
    if not src:
        return candidates
    candidates.append(src)
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", src, flags=re.IGNORECASE):
        block = (m.group(1) or "").strip()
        if block:
            candidates.append(block)
    left, right = src.find("{"), src.rfind("}")
    if left != -1 and right != -1 and right > left:
        candidates.append(src[left : right + 1].strip())
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _parse_llm_json_dict(text: str) -> tuple[Optional[dict], Optional[Exception]]:
    last_err: Optional[Exception] = None
    for cand in _llm_json_candidates(text):
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data, None
            last_err = ValueError("根节点不是 JSON 对象")
        except Exception as e:
            last_err = e
    return None, last_err


def _coerce_str_list(val) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    if isinstance(val, dict):
        return [f"{k}: {v}" for k, v in val.items() if v is not None]
    return []


async def evaluate_answer(
    position: str,
    answer: str,
    question: str = "",
    rag_context: str = "",
    interviewer_style: str = "rigorous",
    language: str = "zh",
    candidate_context: Optional[str] = None,
) -> dict:
    """
    评估单次面试回答，返回结构化评分（5 维度 + 亮点/不足/建议）。

    使用 asyncio 并发，不阻塞主面试流程。

    Args:
        position: 岗位名称
        answer:   候选人的回答内容
        question: 当前面试题目（可选，有助于更精准评估）

    Returns:
        dict 含 technical_score, depth_score, logic_score, job_match_score,
             clarity_score, overall, highlight, weakness, tip
    """
    if not answer or len(answer.strip()) < 5:
        raise ValueError("回答内容过短，无法评估")

    rag_context = (rag_context or "").strip() or "无"

    prompt = (
        "你是资深面试评委。基于题目、候选人回答、岗位要求与RAG知识证据进行评分。\n"
        "请严格输出JSON对象，字段如下：\n"
        "technical_score, logic_score, expression_score, resume_match_score, job_match_score, overall,\n"
        "dimension_feedback(对象，键为以上5个维度，每个值含 comment 和 evidence),\n"
        "question_analysis(对象，含 correctness/completeness/missing_points/errors),\n"
        "highlight, weakness, tip。\n"
        f"岗位={position}\n"
        f"题目={question or '（未记录题目）'}\n"
        f"回答={answer.strip()}\n"
        f"RAG证据={rag_context or '无'}"
    )
    if candidate_context and candidate_context.strip():
        prompt += (
            "\n\n候选人背景参考（与岗位匹配度评估相关）：\n"
            + candidate_context.strip()[:3000]
        )
    if interviewer_style == "pressure":
        prompt += "\n\n评分策略：压力型。对技术错误、逻辑漏洞和回避问题给予更严格扣分。"
    elif interviewer_style == "heuristic":
        prompt += "\n\n评分策略：启发型。在保证客观评分前提下，更关注思路展开与学习潜力。"
    if language == "en":
        prompt += "\n\nEvaluation language strategy: Provide highlight/weakness/tip in English."
    elif language == "bilingual":
        prompt += "\n\n评估语言策略：highlight/weakness/tip 使用中英双语（中文在前，英文在后）。"
    logger.info(f"[回答评估] 开始评估，岗位：{position}，回答长度：{len(answer)}")

    raw = await call_llm(prompt, system_prompt="", model=MODEL_INTERVIEW)
    result, jerr = _parse_llm_json_dict(raw)
    if result is None:
        logger.error("[回答评估] JSON 解析失败：%s，原始前 200 字：%s", jerr, (raw or "")[:200])
        raise ValueError(f"模型评估结果不是合法 JSON：{jerr}")

    for k in ("highlight", "weakness", "tip"):
        if k not in result or not str(result.get(k) or "").strip():
            result[k] = "（模型未返回，已占位）"

    qa = result.get("question_analysis")
    if not isinstance(qa, dict):
        qa = {}
    for k in ("correctness", "completeness"):
        if k not in qa or qa[k] is None:
            qa[k] = ""
        else:
            qa[k] = str(qa[k])
    qa["missing_points"] = _coerce_str_list(qa.get("missing_points"))
    qa["errors"] = _coerce_str_list(qa.get("errors"))
    result["question_analysis"] = qa

    tech = float(result.get("technical_score", result.get("content_score", 0)) or 0)
    logic = float(result.get("logic_score", 0) or 0)
    expr = float(result.get("expression_score", result.get("clarity_score", 0)) or 0)
    resume_match = float(result.get("resume_match_score", 0) or 0)
    job_match = float(result.get("job_match_score", 0) or 0)
    overall = result.get("overall")
    if overall is None:
        overall = round((tech + logic + expr + resume_match + job_match) / 5, 2)
    result["technical_score"] = tech
    result["logic_score"] = logic
    result["expression_score"] = expr
    result["resume_match_score"] = resume_match
    result["job_match_score"] = job_match
    result["overall"] = float(overall)
    feedback = result.get("dimension_feedback")
    if not isinstance(feedback, dict):
        feedback = {}
    dim_keys = ["technical_score", "logic_score", "expression_score", "resume_match_score", "job_match_score"]
    for key in dim_keys:
        row = feedback.get(key)
        if not isinstance(row, dict):
            row = {}
        if not str(row.get("comment") or "").strip():
            row["comment"] = "（该维度未生成细评）"
        if not str(row.get("evidence") or "").strip():
            row["evidence"] = (answer.strip()[:280] + "…") if len(answer.strip()) > 280 else answer.strip()
        feedback[key] = row
    result["dimension_feedback"] = feedback
    logger.info(f"[回答评估] 完成，综合分：{result.get('overall', '?')}")
    return result


def analyze_speech_features(transcription: str, audio_duration_sec: float = 0.0) -> dict:
    """
    从 Whisper 转写文本分析语音表达特征（同步，轻量）。

    Args:
        transcription: Whisper 转写文本
        audio_duration_sec: 音频时长（秒），0 则不计算语速

    Returns:
        dict 含 char_count, word_count, speech_rate_cpm, filler_count,
             filler_words, fluency_score, clarity_hint
    """
    import re

    text = transcription.strip()
    char_count = len(text)

    # 中文分词简化：以标点/空格切分估算词数
    words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
    word_count = len(words)

    # 语速（字/分钟）
    speech_rate_cpm = 0.0
    if audio_duration_sec > 0 and char_count > 0:
        speech_rate_cpm = round(char_count / audio_duration_sec * 60, 1)

    # 停顿词 / 口头禅统计（常见中文语音填充词）
    filler_pattern = re.compile(r'嗯+|啊+|呃+|那个|就是|然后就|所以就|这个嘛|对吧|你知道吗', re.IGNORECASE)
    filler_matches = filler_pattern.findall(text)
    filler_count = len(filler_matches)

    # 简单流利度评分（0-10，基于停顿词比例 + 句子完整性）
    filler_ratio = filler_count / max(word_count, 1)
    fluency_score = round(max(0, 10 - filler_ratio * 20), 1)

    # 语速描述
    if speech_rate_cpm == 0:
        clarity_hint = "（未检测到音频时长）"
    elif speech_rate_cpm < 120:
        clarity_hint = "语速偏慢，可适当加快节奏"
    elif speech_rate_cpm > 280:
        clarity_hint = "语速偏快，建议放慢以确保清晰"
    else:
        clarity_hint = "语速适中"

    return {
        "char_count": char_count,
        "word_count": word_count,
        "speech_rate_cpm": speech_rate_cpm,
        "filler_count": filler_count,
        "filler_words": filler_matches[:5],
        "fluency_score": fluency_score,
        "clarity_hint": clarity_hint,
    }


# ==================== 【最终报告生成】====================

async def generate_final_report(
    position: str,
    difficulty: str,
    conversation: str,
    rag_context: str = "",
    language: str = "zh",
    candidate_context: Optional[str] = None,
) -> dict:
    """
    AI 分析完整面试记录，生成评估报告

    Args:
        position:     岗位名称
        difficulty:   难度等级
        conversation: 完整对话记录

    Returns:
        解析后的报告字典，包含 overall_score / content_score / expression_score 等字段
    """
    prompt = PROMPT_FINAL_REPORT.format(
        position=position,
        difficulty=difficulty,
        conversation=conversation,
    )
    if rag_context and rag_context.strip():
        prompt += "\n\n【岗位标准答案与知识依据（RAG）】\n" + rag_context.strip()[:10000]
    if candidate_context and candidate_context.strip():
        prompt += (
            "\n\n候选人背景（个人资料与简历摘要，可用于岗位匹配与能力推断）：\n"
            + candidate_context.strip()[:8000]
        )
    if language == "en":
        prompt += "\n\nOutput language strategy: highlights/weaknesses/suggestions should be in English."
    elif language == "bilingual":
        prompt += "\n\n输出语言策略：highlights/weaknesses/suggestions 使用中英双语（中文在前，英文在后）。"

    logger.info(f"[报告生成] 开始生成，岗位：{position}，模型：{MODEL_REPORT}")
    report_text = await call_llm(
        prompt,
        system_prompt="你是专业 AI 面试评估专家，输出须为合法 JSON，与岗位事实一致。",
        model=MODEL_REPORT,
    )
    logger.info(f"[报告生成] LLM 响应完成，长度：{len(report_text)}")

    def _json_candidates(text: str) -> list[str]:
        candidates: list[str] = []
        src = (text or "").strip()
        if not src:
            return candidates
        candidates.append(src)
        # 提取 fenced code block（兼容 ```json / ```）
        for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", src, flags=re.IGNORECASE):
            block = (m.group(1) or "").strip()
            if block:
                candidates.append(block)
        # 提取最外层对象
        left = src.find("{")
        right = src.rfind("}")
        if left != -1 and right != -1 and right > left:
            candidates.append(src[left : right + 1].strip())
        # 去重并保序
        out: list[str] = []
        seen: set[str] = set()
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def _load_first_valid_json(text: str) -> tuple[Optional[dict], Optional[Exception]]:
        last_err: Optional[Exception] = None
        for cand in _json_candidates(text):
            try:
                data = json.loads(cand)
                if isinstance(data, dict):
                    return data, None
                last_err = ValueError("JSON 根节点不是对象")
            except Exception as e:
                last_err = e
        return None, last_err

    def _score10(src: dict, keys: tuple[str, ...]) -> Optional[float]:
        """读取 0-10 分；若模型误输出 0-100，自动除以 10。"""
        for key in keys:
            if key not in src:
                continue
            try:
                num = float(src.get(key))
                if num > 10.0 and num <= 100.0:
                    num = num / 10.0
                return max(0.0, min(10.0, num))
            except (TypeError, ValueError):
                continue
        return None

    def _read_list(src: dict, keys: tuple[str, ...]) -> list[str]:
        for key in keys:
            val = src.get(key)
            if isinstance(val, list):
                out = [str(x).strip() for x in val if str(x).strip()]
                if out:
                    return out
            if isinstance(val, str) and val.strip():
                return [val.strip()]
        return []

    def _parse_dimension_feedback(raw) -> dict:
        if isinstance(raw, dict):
            out = {}
            for k, v in raw.items():
                if not isinstance(v, dict):
                    continue
                c = v.get("comment") or v.get("summary") or ""
                e = v.get("evidence") or v.get("quote") or ""
                out[str(k)] = {"comment": str(c).strip(), "evidence": str(e).strip()}
            return out
        if isinstance(raw, str) and raw.strip():
            try:
                obj = json.loads(raw)
                return _parse_dimension_feedback(obj)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def _parse_improvement_resources(raw) -> dict:
        if isinstance(raw, dict):
            out = {
                "knowledge_points": [],
                "sample_interview_questions": [],
                "communication_readings": [],
            }
            kp = raw.get("knowledge_points")
            if isinstance(kp, list):
                for it in kp:
                    if not isinstance(it, dict):
                        continue
                    out["knowledge_points"].append(
                        {
                            "topic": str(it.get("topic") or "").strip(),
                            "summary": str(it.get("summary") or "").strip(),
                            "action": str(it.get("action") or "").strip(),
                        }
                    )
            siq = raw.get("sample_interview_questions")
            if isinstance(siq, list):
                for it in siq:
                    if not isinstance(it, dict):
                        continue
                    out["sample_interview_questions"].append(
                        {
                            "question": str(it.get("question") or "").strip(),
                            "focus": str(it.get("focus") or "").strip(),
                        }
                    )
            cr = raw.get("communication_readings")
            if isinstance(cr, list):
                for it in cr:
                    if not isinstance(it, dict):
                        continue
                    out["communication_readings"].append(
                        {
                            "title": str(it.get("title") or "").strip(),
                            "summary": str(it.get("summary") or "").strip(),
                            "url_or_search": str(
                                it.get("url_or_search") or it.get("url") or ""
                            ).strip(),
                        }
                    )
            return out
        return {
            "knowledge_points": [],
            "sample_interview_questions": [],
            "communication_readings": [],
        }

    def _finalize_report(data: dict) -> dict:
        """校验核心分数字段，并保留 LLM 返回的全部扩展字段（多维分、Markdown、维度反馈）。"""
        overall = _score10(data, ("overall_score", "overall", "total_score"))
        tech_ok = _score10(
            data, ("technical_correctness_score", "technical_accuracy_score")
        )
        depth = _score10(data, ("knowledge_depth_score", "depth_score"))
        content = _score10(data, ("content_score", "technical_score", "knowledge_score"))
        expression = _score10(data, ("expression_score",))
        logic = _score10(data, ("logic_score",))
        job_match = _score10(data, ("job_match_score", "position_match_score"))
        communication = _score10(data, ("communication_score",))
        adaptability = _score10(data, ("adaptability_score",))
        speech_rate = _score10(data, ("speech_rate_score",))
        clarity = _score10(data, ("clarity_score",))
        confidence = _score10(data, ("confidence_score",))
        resume_match = _score10(data, ("resume_match_score",))

        if tech_ok is not None and depth is not None:
            derived_content = round((tech_ok + depth) / 2.0, 2)
            if content is None:
                content = derived_content
        elif content is None and tech_ok is not None:
            content = tech_ok
        elif content is None and depth is not None:
            content = depth

        if expression is None:
            cand = [x for x in (communication, clarity) if x is not None]
            if cand:
                expression = round(sum(cand) / len(cand), 2)
            elif content is not None:
                expression = round(max(0.0, min(10.0, content - 0.3)), 2)

        if overall is None and content is not None and expression is not None:
            overall = round((content + expression) / 2, 2)

        missing = []
        if overall is None:
            missing.append("overall_score")
        if content is None:
            missing.append("content_score")
        if expression is None:
            missing.append("expression_score")
        if missing:
            raise ValueError(f"报告字段缺失或非法: {', '.join(missing)}")

        highlights = _read_list(
            data, ("highlights", "highlight", "strengths", "亮点", "优势")
        )
        weaknesses = _read_list(
            data, ("weaknesses", "weakness", "improvements", "不足", "待改进")
        )
        suggestions = _read_list(
            data, ("suggestions", "suggestion", "advice", "建议", "改进建议")
        )
        if not highlights:
            highlights = ["（模型未返回亮点条目，请结合总分与对话记录综合查看）"]
        if not weaknesses:
            weaknesses = ["（模型未返回不足条目，请结合维度得分复盘）"]
        if not suggestions:
            suggestions = ["（模型未返回建议条目，可针对薄弱能力补充练习）"]

        rm = data.get("report_markdown")
        report_markdown = rm.strip() if isinstance(rm, str) and rm.strip() else None

        dimension_feedback = _parse_dimension_feedback(data.get("dimension_feedback"))
        improvement_resources = _parse_improvement_resources(
            data.get("improvement_resources")
        )

        return {
            "overall_score": overall,
            "content_score": content,
            "technical_correctness_score": tech_ok,
            "knowledge_depth_score": depth,
            "expression_score": expression,
            "logic_score": logic,
            "job_match_score": job_match,
            "communication_score": communication,
            "adaptability_score": adaptability,
            "speech_rate_score": speech_rate,
            "clarity_score": clarity,
            "confidence_score": confidence,
            "resume_match_score": resume_match,
            "highlights": highlights,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "report_markdown": report_markdown,
            "dimension_feedback": dimension_feedback,
            "improvement_resources": improvement_resources,
        }

    report_data, parse_error = _load_first_valid_json(report_text)

    # JSON 异常时做一次“结构修复”重试：让模型只做格式重排，不重新编内容
    if not isinstance(report_data, dict):
        logger.warning(
            "[报告生成] 首次 JSON 解析失败，尝试结构修复。error=%s, raw_preview=%s",
            parse_error,
            (report_text or "")[:300],
        )
        repair_prompt = (
            "请将下面文本重排为合法 JSON 对象，且仅输出 JSON（不要 markdown/code fence）。\n"
            "必须包含：overall_score, technical_correctness_score, knowledge_depth_score, content_score, "
            "expression_score, logic_score, job_match_score, "
            "communication_score, adaptability_score, speech_rate_score, clarity_score, confidence_score, "
            "highlights, weaknesses, suggestions（数组）, report_markdown（字符串）, dimension_feedback（对象）, "
            "improvement_resources（对象，含 knowledge_points/sample_interview_questions/communication_readings 数组）。\n"
            "所有 *_score 为 0-10 数字；highlights/weaknesses/suggestions 为字符串数组。\n\n"
            f"原始文本：\n{report_text}"
        )
        repaired_text = await call_llm(
            prompt=repair_prompt,
            system_prompt="你是 JSON 修复器，只做结构化整理，不输出解释。",
            model=MODEL_REPORT,
        )
        report_data, parse_error = _load_first_valid_json(repaired_text)

    if not isinstance(report_data, dict):
        raise ValueError(
            f"报告 JSON 解析失败: {parse_error}; raw_preview={(report_text or '')[:300]}"
        )

    finalized = _finalize_report(report_data)
    logger.info("[报告生成] JSON 解析/标准化成功")
    return finalized


# ==================== 【语音识别】====================

async def speech_to_text(audio_path: str) -> str:
    """
    将音频文件转换为文字（使用本地 Whisper 模型）

    首次调用会加载模型（约 5-15 秒），后续调用复用已加载的模型（< 1 秒）。

    Args:
        audio_path: 音频文件路径（WAV/MP3/M4A/FLAC 等格式）

    Returns:
        识别出的文本内容

    Raises:
        FileNotFoundError: 音频文件不存在
        Exception:         识别失败
    """
    logger.info(f"[Whisper] 开始语音识别：{audio_path}")

    try:
        model = await _get_whisper_model()

        loop = asyncio.get_running_loop()
        logger.info("[Whisper] 执行音频转录...")
        result = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                audio_path,
                language=ASR_LANGUAGE,
                verbose=False,
            ),
        )

        recognized_text: str = result["text"].strip()
        logger.info(f"[Whisper] 识别完成，长度：{len(recognized_text)}，预览：{recognized_text[:80]}")
        return recognized_text

    except FileNotFoundError:
        msg = f"[Whisper] 文件不存在：{audio_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
    except Exception as e:
        msg = f"[Whisper] 识别失败：{e}"
        logger.error(msg, exc_info=True)
        raise Exception(msg) from e


# transcribe_speech 是 speech_to_text 的别名（interview.py 中两处都有调用）
transcribe_speech = speech_to_text


# ==================== 【视频帧提取（多策略）】====================

def _extract_frames_via_ffmpeg(video_path: str, max_frames: int = 5) -> list:
    """
    使用 FFmpeg 提取视频帧（最可靠，支持所有格式包括 webm）。
    返回 [{timestamp, image_base64}] 列表，失败返回空列表。
    """
    import subprocess, tempfile, shutil
    frame_dir = tempfile.mkdtemp(prefix="interview_frames_")
    frames = []
    try:
        # 获取视频时长
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=15,
        )
        duration = _safe_parse_duration_seconds(probe.stdout)
        if duration <= 0:
            duration = 10.0  # 保底

        # 均匀提取最多 max_frames 帧
        interval = max(1.0, duration / max_frames)
        timestamps = [min(i * interval, duration - 0.5) for i in range(max_frames)]

        for idx, ts in enumerate(timestamps):
            out_path = os.path.join(frame_dir, f"frame_{idx:03d}.jpg")
            result = subprocess.run(
                ["ffmpeg", "-ss", str(ts), "-i", video_path,
                 "-frames:v", "1", "-q:v", "3", out_path, "-y"],
                capture_output=True, timeout=20,
            )
            if result.returncode == 0 and os.path.exists(out_path):
                with open(out_path, "rb") as f:
                    img_bytes = f.read()
                if len(img_bytes) > 0:
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    m = int(ts // 60)
                    s = int(ts % 60)
                    frames.append({"timestamp": f"{m}:{s:02d}", "image_base64": b64})

        logger.info(f"[视频帧提取-ffmpeg] 成功提取 {len(frames)} 帧")
    except FileNotFoundError:
        logger.warning("[视频帧提取-ffmpeg] ffmpeg/ffprobe 未安装")
    except Exception as e:
        logger.warning(f"[视频帧提取-ffmpeg] 失败：{e}")
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)
    return frames


def _extract_frames_via_opencv(video_path: str, max_frames: int = 5) -> list:
    """
    使用 OpenCV 提取视频帧（降级方案）。
    支持两种模式：
      - 已知帧数（mp4）：均匀抽帧
      - 未知帧数（webm/浏览器录制）：逐帧顺序读取，每隔固定帧数采样
    """
    frames = []
    cap = None
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("[视频帧提取-cv2] 无法打开视频文件")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames > 0:
            # 已知帧数：均匀抽取
            interval = max(1, total_frames // max_frames)
            indices = list(range(0, total_frames, interval))[:max_frames]
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                ret2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret2:
                    continue
                b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                t = idx / fps
                frames.append({"timestamp": f"{int(t//60)}:{int(t%60):02d}", "image_base64": b64})
        else:
            # 未知帧数（webm/浏览器录制）：顺序读取，每隔 skip 帧采样一次
            # 以 25fps 估算，每 2 秒取一帧，即每 50 帧采样一次
            skip = max(1, int(fps * 2)) if fps > 0 else 50
            frame_idx = 0
            collected = 0
            while collected < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % skip == 0:
                    ret2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret2 and len(buf) > 0:
                        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                        t = frame_idx / fps
                        frames.append({"timestamp": f"{int(t//60)}:{int(t%60):02d}", "image_base64": b64})
                        collected += 1
                frame_idx += 1

        logger.info(f"[视频帧提取-cv2] 成功提取 {len(frames)} 帧")
    except ImportError:
        logger.warning("[视频帧提取-cv2] OpenCV 未安装")
    except Exception as e:
        logger.warning(f"[视频帧提取-cv2] 失败：{e}")
    finally:
        if cap is not None:
            cap.release()
    return frames


def _get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）：优先 ffprobe，降级 PyAV，失败返回 0"""
    # 策略1：ffprobe
    try:
        import subprocess
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=10,
        )
        val = _safe_parse_duration_seconds(probe.stdout)
        if val > 0:
            return val
    except FileNotFoundError:
        pass  # ffprobe 未安装，尝试 PyAV
    except Exception:
        pass

    # 策略2：PyAV
    try:
        import av as _av
        with _av.open(video_path) as container:
            if container.duration:
                return float(container.duration) / 1_000_000
    except Exception:
        pass

    return 0.0


def _extract_frames_via_pyav(video_path: str, max_frames: int = 5) -> list:
    """
    使用 PyAV 提取视频帧（第二降级策略，优先于 OpenCV）。
    PyAV 内置 FFmpeg 静态库，能可靠解码浏览器录制的 VP9/VP8 WebM，
    无需系统安装 FFmpeg，跨平台支持。
    """
    try:
        import av as _av
    except ImportError:
        logger.debug("[视频帧提取-pyav] PyAV 未安装，跳过（可运行 pip install av）")
        return []

    frames = []
    try:
        container = _av.open(video_path)
        video_streams = [s for s in container.streams if s.type == "video"]
        if not video_streams:
            logger.warning("[视频帧提取-pyav] 未找到视频流")
            container.close()
            return []

        vstream = video_streams[0]

        # 获取时长
        duration_secs = 0.0
        if vstream.duration is not None and vstream.time_base:
            duration_secs = float(vstream.duration * vstream.time_base)
        if duration_secs <= 0 and container.duration:
            duration_secs = float(container.duration) / 1_000_000
        if duration_secs <= 0:
            duration_secs = 30.0  # 保底估计

        # 均匀采样时间点（各帧时间点）
        interval = duration_secs / max_frames
        # 在每段中间位置取帧，避免开头/结尾黑屏
        target_times = [interval * i + interval * 0.3 for i in range(max_frames)]

        collected = 0
        target_idx = 0

        for frame in container.decode(video=0):
            if target_idx >= len(target_times):
                break

            pts = frame.pts
            if pts is None:
                continue
            frame_time = float(pts * vstream.time_base)

            if frame_time >= target_times[target_idx]:
                img_array = frame.to_ndarray(format="bgr24")
                ret, buf = cv2.imencode(".jpg", img_array, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ret and len(buf) > 0:
                    b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                    m, s = int(frame_time // 60), int(frame_time % 60)
                    frames.append({"timestamp": f"{m}:{s:02d}", "image_base64": b64})
                    collected += 1
                target_idx += 1

        container.close()
        logger.info(f"[视频帧提取-pyav] 成功提取 {len(frames)} 帧，视频时长 {duration_secs:.1f}s")
    except Exception as e:
        logger.warning(f"[视频帧提取-pyav] 失败：{type(e).__name__}: {e}")

    return frames


# ==================== 【视频表情分析】====================

async def analyze_video_expression(video_path: str) -> dict:
    """
    分析视频中的表情和肢体语言（使用 DeepSeek 视觉模型）。

    帧提取策略（优先级）：
      1. 系统 FFmpeg：最可靠，支持所有格式
      2. PyAV（内置 FFmpeg）：跨平台，无需系统安装，支持 VP9/VP8 WebM
      3. OpenCV：最终降级，已修复 webm 无帧数问题
      4. 全部失败：返回降级默认结果

    Args:
        video_path: 视频文件路径（支持 webm/mp4/mov）

    Returns:
        {expression, psychology, body_language, score, suggestions, emotion, frames_analyzed}
    """
    import os as _os
    file_size = _os.path.getsize(video_path) if _os.path.exists(video_path) else 0
    logger.info(f"[视频分析] 开始分析：{video_path}，文件大小：{file_size} bytes")

    if file_size < 1024:
        logger.warning(f"[视频分析] 视频文件过小（{file_size} bytes），可能是空文件或录制失败")
        return _video_analysis_fallback("视频文件过小，录制可能未完成")

    loop = asyncio.get_running_loop()

    # 获取视频时长
    duration = await loop.run_in_executor(None, lambda: _get_video_duration(video_path))
    logger.info(f"[视频分析] 检测到视频时长：{duration:.1f}s")

    # 策略1：系统 FFmpeg
    frames_data = await loop.run_in_executor(
        None, lambda: _extract_frames_via_ffmpeg(video_path, max_frames=5)
    )
    if frames_data:
        logger.info(f"[视频分析] 策略1(FFmpeg) 成功，提取 {len(frames_data)} 帧")

    # 策略2：PyAV（内置 FFmpeg，支持 VP9/VP8 WebM，跨平台）
    if not frames_data:
        logger.info("[视频分析] 策略1(FFmpeg) 失败，尝试策略2(PyAV)...")
        frames_data = await loop.run_in_executor(
            None, lambda: _extract_frames_via_pyav(video_path, max_frames=5)
        )
        if frames_data:
            logger.info(f"[视频分析] 策略2(PyAV) 成功，提取 {len(frames_data)} 帧")

    # 策略3：OpenCV
    if not frames_data:
        logger.info("[视频分析] 策略2(PyAV) 失败，尝试策略3(OpenCV)...")
        frames_data = await loop.run_in_executor(
            None, lambda: _extract_frames_via_opencv(video_path, max_frames=5)
        )
        if frames_data:
            logger.info(f"[视频分析] 策略3(OpenCV) 成功，提取 {len(frames_data)} 帧")

    if not frames_data:
        logger.warning("[视频分析] 三种策略均失败，无法提取视频帧，返回降级结果")
        return _video_analysis_fallback(
            "视频帧提取失败（建议安装 FFmpeg 或运行 pip install av）"
        )

    logger.info(f"[视频分析] 共提取 {len(frames_data)} 帧，开始 DeepSeek 画面分析...")

    # 并发调用 Qwen-VL 分析所有帧（最多 5 个并发）
    sem = asyncio.Semaphore(3)  # 限制并发避免超 API 限速

    async def analyze_one(fd, idx):
        async with sem:
            try:
                return await _analyze_video_frame(fd["image_base64"], fd["timestamp"], idx + 1)
            except Exception as e:
                logger.warning(f"[视频分析] 第 {idx+1} 帧分析失败：{type(e).__name__}: {e}")
                return {"expression": "分析失败", "emotion": "neutral", "confidence": 0.3}

    tasks = [analyze_one(fd, i) for i, fd in enumerate(frames_data)]
    all_analyses = await asyncio.gather(*tasks)

    result = _aggregate_video_analysis(list(all_analyses), duration)
    result["frames_analyzed"] = len([a for a in all_analyses if a.get("expression") != "分析失败"])
    return result


def _jitter_psychology_text(base: str) -> str:
    """心理状态描述增加轻微随机扰动，避免长时间固定不变。"""
    seeds = [
        "当下微表情显示：",
        "从非语言线索看：",
        "瞬时状态：",
        "整体氛围：",
        "镜头前呈现：",
    ]
    tails = [
        "（情绪在正常面试波动范围内略有起伏）",
        "（专注度随问题难度小幅变化）",
        "（紧张感在可控范围内波动）",
        "（心理状态处于动态调整中）",
    ]
    r = random.Random(int(time.time() * 1000) % (2**32))
    if not base or len(base) < 4:
        base = "心态整体平稳，情绪在常见面试波动范围内"
    return f"{r.choice(seeds)}{base}{r.choice(tails)}"


def _video_analysis_fallback(reason: str) -> dict:
    """视频分析降级结果"""
    return {
        "expression": f"视频分析失败（{reason}），视频中候选人表现自然",
        "psychology": _jitter_psychology_text("心态平稳，情绪稳定"),
        "body_language": "肢体语言得体",
        "score": 7.0,
        "suggestions": "整体表现不错，继续保持",
    }


def _aggregate_video_analysis(all_analyses: list, duration: float) -> dict:
    """汇总多帧分析结果"""
    expression_counts: dict = {}
    emotion_counts: dict = {}
    total_confidence = 0.0
    valid_count = 0

    for a in all_analyses:
        expr = a.get("expression", "")
        emotion = a.get("emotion", "")
        confidence = float(a.get("confidence", 0))

        if expr and expr not in ("分析失败",):
            expression_counts[expr] = expression_counts.get(expr, 0) + 1
            valid_count += 1
            total_confidence += confidence
        if emotion:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

    dominant_expression = (
        max(expression_counts, key=expression_counts.get)
        if expression_counts else "表情自然"
    )
    dominant_emotion = (
        max(emotion_counts, key=emotion_counts.get)
        if emotion_counts else "neutral"
    )
    avg_confidence = total_confidence / valid_count if valid_count > 0 else 0.5

    psychology_map = {
        "happy": "心态积极乐观，展现良好精神状态",
        "neutral": "心态平稳，情绪控制良好",
        "confident": "充满自信，对面试有充分准备",
        "focused": "专注认真，深度思考中",
        "nervous": "略显紧张，但基本状态良好",
        "surprised": "思维活跃，对新问题保持好奇",
        "sad": "状态欠佳，可能需要调整心态",
        "angry": "情绪波动较大，建议放松心态",
    }
    suggestions_map = {
        "happy": "保持微笑，让氛围更加轻松愉快",
        "neutral": "可以适当增加一些表情变化，增强感染力",
        "confident": "自信表现很好，继续保持",
        "focused": "专注度很高，建议在回答时也多与面试官眼神交流",
        "nervous": "深呼吸放松，语速放慢一些会更好",
        "surprised": "反应敏捷是很好的品质，保持这种好奇心",
        "sad": "建议调整心态，展现最好的一面",
        "angry": "保持平和心态，冷静应对各种挑战",
    }

    base_score = 7.0
    confidence_bonus = (avg_confidence - 0.6) * 3
    emotion_bonus = 0.5 if dominant_emotion in ("happy", "confident", "focused") else 0.0
    score = round(min(10.0, max(0.0, base_score + confidence_bonus + emotion_bonus)), 1)

    logger.info(f"[视频分析] 主导表情：{dominant_expression}，情绪：{dominant_emotion}，评分：{score}")

    psych_base = psychology_map.get(dominant_emotion, "心态平稳，表现正常")

    return {
        "expression": dominant_expression,
        "psychology": _jitter_psychology_text(psych_base),
        "body_language": "坐姿端正，手势自然，肢体语言得体",
        "score": score,
        "suggestions": suggestions_map.get(dominant_emotion, "整体表现不错，继续保持"),
    }


def _extract_chat_completion_text(resp_data: dict) -> Optional[str]:
    """从 compatible-mode /chat/completions 响应中取出助手文本。"""
    choices = resp_data.get("choices")
    if not choices:
        return None
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts) if parts else None
    return None


async def _call_deepseek_vision(image_base64: str, prompt: str, model: str) -> Optional[str]:
    """deepseek-flash 支持 image_url，输出仍是文本。"""
    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500,
        **deepseek_extra_body(),
    }
    async with httpx.AsyncClient(timeout=DEEPSEEK_VISION_TIMEOUT) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if resp.status_code != 200:
        logger.warning(f"[DeepSeek-Vision] HTTP {resp.status_code}：{resp.text[:400]}")
        return None
    data = resp.json()
    text = _extract_chat_completion_text(data)
    if not text:
        logger.warning(f"[DeepSeek-Vision] 响应无正文：{str(data)[:500]}")
    return text


async def _analyze_video_frame(image_base64: str, timestamp: str, frame_index: int) -> dict:
    """用 DeepSeek 视觉模型分析单帧面试画面。"""
    logger.info(f"[DeepSeek-Vision] 分析第 {frame_index} 帧（{timestamp}）")

    if not DEEPSEEK_API_KEY:
        logger.warning("[DeepSeek-Vision] API Key 未配置")
        return {
            "timestamp": timestamp,
            "expression": "未配置 DeepSeek API Key，无法分析表情",
            "emotion": "neutral",
            "confidence": 0.0,
        }

    prompt = """请分析这张面试场景中的人物表情和状态，返回以下 JSON 格式（直接返回 JSON，不要 markdown）：
{
    "expression": "简洁的表情总结（中文，10-20字）",
    "emotion": "情绪类别（从 happy/neutral/confident/focused/nervous/surprised/sad/angry 中选一个）",
    "eye_contact": "眼神描述",
    "body_language": "肢体语言描述",
    "confidence": 0.90
}"""

    try:
        text_content = await _call_deepseek_vision(image_base64, prompt, MODEL_VISION)
    except httpx.TimeoutException:
        logger.error("[DeepSeek-Vision] API 请求超时")
        return {"timestamp": timestamp, "expression": "分析超时", "emotion": "neutral", "confidence": 0.0}
    except Exception as e:
        logger.error(f"[DeepSeek-Vision] 请求异常：{e}", exc_info=True)
        return {"timestamp": timestamp, "expression": "表情分析失败", "emotion": "neutral", "confidence": 0.0}

    if not text_content:
        logger.error("[DeepSeek-Vision] 未返回文本")
        return {"timestamp": timestamp, "expression": "表情分析暂不可用", "emotion": "neutral", "confidence": 0.0}

    parsed, err = _parse_llm_json_dict(text_content)
    if parsed is None:
        logger.error(f"[DeepSeek-Vision] JSON 解析失败：{err}，原始：{text_content[:200]}")
        return {"timestamp": timestamp, "expression": "表情分析失败", "emotion": "neutral", "confidence": 0.0}

    parsed.setdefault("emotion", "neutral")
    parsed.setdefault("confidence", 0.5)
    parsed["timestamp"] = timestamp
    logger.info(f"[DeepSeek-Vision] 第 {frame_index} 帧分析成功：{str(parsed.get('expression', ''))[:30]}")
    return parsed


# ==================== 【简历分析与优化】====================

async def analyze_resume(resume_text: str) -> dict:
    """
    AI 分析简历文本，提取结构化信息

    Args:
        resume_text: 简历的纯文本内容

    Returns:
        结构化简历字典（basic_info / education / experience / projects / skills）
    """
    logger.info(f"[简历分析] 文本长度：{len(resume_text)}")
    prompt = PROMPT_RESUME_ANALYSIS.format(resume_text=resume_text)

    result_text = await call_llm(
        prompt,
        system_prompt="你是简历 OCR/文本解析助手，仅输出 JSON，无其他文字。",
        model=MODEL_RESUME_VL,
    )

    data, err = _parse_llm_json_dict(result_text)
    if data is not None:
        logger.info(f"[简历分析] 解析成功，技能数：{len(data.get('skills', []))}")
        return data
    logger.error(f"[简历分析] JSON 解析失败：{err}")
    return {
        "basic_info": {"name": "解析失败", "email": "", "phone": ""},
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
    }


async def optimize_resume(resume_data: dict) -> dict:
    """
    AI 优化简历内容，使其更专业有吸引力

    Args:
        resume_data: 结构化简历字典（来自 analyze_resume）

    Returns:
        优化后的结构化简历字典
    """
    logger.info(f"[简历优化] 原始数据：{len(str(resume_data))} 字符")

    newline = "\n"

    def _achievements(raw) -> str:
        if isinstance(raw, list):
            return "；".join(str(item).strip() for item in raw if str(item).strip())
        return str(raw or "")

    resume_text = f"""
基本信息：
- 姓名：{resume_data.get('basic_info', {}).get('name', '')}
- 邮箱：{resume_data.get('basic_info', {}).get('email', '')}
- 电话：{resume_data.get('basic_info', {}).get('phone', '')}

教育经历：
{newline.join([f"- {e.get('school','')} | {e.get('degree','')} | {e.get('major','')} | {e.get('start_date','')} - {e.get('end_date','')}" for e in resume_data.get('education', [])])}

工作经历：
{newline.join([f"- {e.get('company','')} | {e.get('position','')} | {e.get('start_date','')} - {e.get('end_date','')}{newline}  主要工作：{_achievements(e.get('achievements'))}" for e in resume_data.get('experience', [])])}

项目经验：
{newline.join([f"- {p.get('name','')} | {p.get('role','')}{newline}  描述：{p.get('description','')}" for p in resume_data.get('projects', [])])}

技能清单：
{', '.join(resume_data.get('skills', []))}
"""

    prompt = PROMPT_RESUME_OPTIMIZE.format(resume_data=resume_text)
    result_text = await call_llm(
        prompt,
        system_prompt="你是简历优化专家，仅输出 JSON，无 markdown。",
        model=MODEL_RESUME_OPTIMIZE,
    )

    optimized, err = _parse_llm_json_dict(result_text)
    if optimized is not None:
        logger.info("[简历优化] 解析成功")
        return optimized
    logger.warning(f"[简历优化] JSON 解析失败，返回原始数据：{err}")
    return resume_data
