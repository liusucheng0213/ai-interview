"""
LLM 配置模块 - 阿里云百炼 DashScope（LangChain 集成）

七类模型分工（环境变量可覆盖，默认值与业务角色对齐）：
1. 向量 Embedding：text-embedding-v3（见 rag_conf.RAG_USE_DASHSCOPE_EMBEDDING，非本文件 Chat模型）
2. 音视频多模态：DASHSCOPE_MODEL_OMNI → qwen3.5-omni-flash（视频帧/多模态分析，低延迟）
3. 面试对话：DASHSCOPE_MODEL_INTERVIEW → qwen-turbo（多轮提问，每次仅一个问题）
4. 报告/成长计划：DASHSCOPE_MODEL_REPORT → qwen-max（长文本结构化评估与路线）
5. 简历解析（视觉/结构化 JSON）：DASHSCOPE_MODEL_RESUME_VL → qwen-vl-max-latest（可改）
6. 知识图谱/入库结构化：DASHSCOPE_MODEL_KNOWLEDGE_GRAPH → qwen-plus（实体关系抽取）
7. 全局兜底：DASHSCOPE_MODEL → qwen-turbo

优化：_build_llm() 按 (model_name, streaming) 缓存 ChatOpenAI 实例。
"""

import logging
import os
from typing import AsyncGenerator, Dict, Optional, Tuple

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()
logger = logging.getLogger(__name__)

# ==================== 环境变量 ====================
DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 默认/回退模型（全局兜底）
DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen-turbo")
DASHSCOPE_TIMEOUT: int = int(os.getenv("DASHSCOPE_TIMEOUT", "60"))

# 3. 面试对话
MODEL_INTERVIEW: str = os.getenv("DASHSCOPE_MODEL_INTERVIEW", "qwen-turbo")
# 4. 报告与成长计划
MODEL_REPORT: str = os.getenv("DASHSCOPE_MODEL_REPORT", "qwen-max")
# 5. 简历解析（结构化 JSON，与视觉简历解析同模型族；默认用最新快照名）
MODEL_RESUME_VL: str = os.getenv("DASHSCOPE_MODEL_RESUME_VL", "qwen-vl-max-latest")
MODEL_RESUME_OPTIMIZE: str = os.getenv("DASHSCOPE_MODEL_RESUME_OPTIMIZE", "qwen-plus")
# 6. 知识图谱 / 入库结构化
MODEL_KNOWLEDGE_GRAPH: str = os.getenv("DASHSCOPE_MODEL_KNOWLEDGE_GRAPH", "qwen-plus")
# 2. 音视频多模态面试分析（视频帧等）
MODEL_OMNI_INTERVIEW: str = os.getenv("DASHSCOPE_MODEL_OMNI", "qwen3.5-omni-flash")

# 视觉模型（Omni 失败时回落）
QWEN_VL_MODEL: str = os.getenv("QWEN_VL_MODEL", MODEL_RESUME_VL)
QWEN_VL_TIMEOUT: int = int(os.getenv("QWEN_VL_TIMEOUT", "60"))
WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "small")
ASR_LANGUAGE: str = os.getenv("ASR_LANGUAGE", "zh")

_api_key_ok = bool(DASHSCOPE_API_KEY and DASHSCOPE_API_KEY != "请填写你的阿里云百炼API_KEY")
if not _api_key_ok:
    logger.warning("DASHSCOPE_API_KEY 未配置，请在 .env 中填写阿里云百炼 API Key")

# ==================== 提示词模板 ====================

PROMPT_GROWTH_ADVICE = """你是一位资深的技术成长顾问，擅长根据候选人的历史面试数据制定个性化提升计划。

以下是候选人的历史面试记录摘要：

岗位：{position}
面试次数：{interview_count} 次
最近各维度平均分（10分制）：
{dimension_summary}
成长趋势：{trend_desc}
历史亮点：{highlights}
历史不足：{weaknesses}

【数据库·岗位技术栈】
{job_tech_block}

【数据库·题库知识点节选（同一岗位）】
{question_bank_excerpt}

【向量库·知识库检索摘录（结合薄弱点）】
{kb_excerpt}

请生成一份详细的个性化能力提升计划，严格按以下 JSON 格式输出（不要有 markdown 包裹）：

{{
  "overall_advice": "整体发展建议（2-3句话，正向积极）",
  "weak_points": [
    {{"dimension": "维度名", "issue": "具体问题描述", "priority": "高/中/低"}}
  ],
  "improvement_plan": [
    {{
      "week": "第1-2周",
      "focus": "聚焦主题",
      "tasks": ["具体任务1", "具体任务2", "具体任务3"],
      "goal": "本阶段目标"
    }}
  ],
  "learning_roadmap": {{
    "position": "{position}",
    "total_weeks": 8,
    "phases": [
      {{
        "phase": "基础强化",
        "weeks": "第1-2周",
        "topics": ["主题1", "主题2"],
        "resources": ["推荐资源/书籍/课程"]
      }}
    ]
  }},
  "practice_suggestions": [
    {{"type": "刷题/项目/阅读/实践", "content": "具体内容", "frequency": "频率"}}
  ],
  "learning_resources": [
    {{"title": "资源标题", "url": "https://...", "topic": "关联主题", "reason": "与候选人薄弱点/岗位的关系"}}
  ],
  "deep_dive_knowledge": [
    {{"topic": "技术知识点", "why": "与薄弱点/岗位的关系", "study_steps": "2-4步可执行学习动作"}}
  ],
  "star_interview_questions": [
    {{"question": "常见或进阶面试题", "answer_outline": "回答要点提纲（STAR/结论-理由-例子）", "pitfalls": "易错点"}}
  ],
  "communication_readings": [
    {{"title": "沟通/表达类主题", "summary": "1-2句可读收获", "url": "https://真实可访问链接", "practice_tip": "一条可立即练习的小技巧"}}
  ],
  "knowledge_graph": {{
    "nodes": [
      {{"id": "n1", "label": "节点名（如：沟通表达）", "group": "skill|weak|goal"}}
    ],
    "edges": [
      {{"from": "n1", "to": "n2", "label": "关系说明（如：支撑/需加强）"}}
    ]
  }},
  "motivational_message": "一句鼓励的话"
}}

要求：
- improvement_plan 至少包含 4 个阶段（覆盖4-8周）
- learning_roadmap 至少 3 个 phase，技术路线要具体可执行
- practice_suggestions 至少 4 条，类型多样
- learning_resources 至少 5 条，url 须为真实可访问的公开学习站点（如官方文档、知名课程、技术社区），与历史薄弱点或目标岗位强相关
- deep_dive_knowledge 至少 4 条，覆盖岗位核心技术栈与历史薄弱点
- star_interview_questions 至少 4 条，难度递进，answer_outline 简洁可背
- communication_readings 至少 3 条，url 优先权威站点（高校公开课、出版社、主流媒体职场专栏）；不确定时用 Wikipedia / Toastmasters 等公认来源
- knowledge_graph 至少 6 个节点、5 条边，体现「岗位目标—能力维度—学习主题」的关联，group 用于前端着色
- 所有建议必须具体、可操作，避免空泛
- 直接输出 JSON，不要有任何额外说明"""

SYSTEM_PROMPT_INTERVIEWER = """你是资深的 AI 技术面试官，具备专业的面试技巧和亲和力。

【模型与保密】
- 面向实时多轮对话：回复须短、准、快；每次只输出一个面试问题（一句追问也算一个问题）。
- 严禁向候选人透露任何评分标准、打分维度、权重或「我在评估你」的系统规则。

【核心职责】
通过多轮渐进式对话，全面评估候选人的技术能力、逻辑思维和综合素质。

【面试节奏三阶段】
① 暖场阶段（第1-2轮）：先聊项目经历，建立对话基础，不出纯考察型技术题
② 深入阶段（第3-7轮）：基于候选人暖场时分享的背景，逐步深入技术细节
③ 压力阶段（第8轮+）：聚焦最薄弱的维度，系统设计/边界条件等进阶话题

【难度管理原则（重要）】
- 每个新话题：必须从最简单的引导性问题开始，不允许直接出难题
- 同一话题内：回答好 → 适当提升难度；回答差 → 换话题而非反复追问
- 切换话题后：难度归零重新开始，第一题必须是入门/开放级

【低质量/不相关回答 — 硬性换话题规则（最高优先级）】
- 候选人回答答非所问或与问题明显无关 → 不再追问，立即切换到全新话题
- 同一话题连续2次回答差（错误/极短/重复失败）→ 果断切换，禁止第3次同类追问
- 候选人说"不知道"/"没接触过" → 给予简短鼓励，换一个更基础的不同话题

【沟通风格】
- 每次只问一个问题，50-150 字
- 适当给出口头鼓励（"好的，思路不错"），保持中立友好氛围
- 避免"你说的不对"等负面评价，改用"那你有没有了解过..."来引导"""

PROMPT_GENERATE_QUESTION = """你正在主持对【{position}】岗位候选人的技术面试（难度设定：{difficulty}，当前第 {round} 轮）。

════════════ 参考知识库 ════════════
{rag_knowledge}
════════════════════════════════════

════════════ 对话摘录（可能已压缩，仅含最近若干轮） ═══════════
{conversation}
════════════════════════════════════

▶ 【第一步：在脑海中完成以下分析，不要输出】
A. 当前轮次阶段：第1-2轮（开场暖场）/ 第3-5轮（技术基础）/ 第6-8轮（技术深度）/ 第9轮+（压力）
B. 候选人上一个回答质量：优秀 / 基本正确 / 有缺漏 / 错误 / 回避不答 / 答非所问 / 放弃
C. 该话题已连续追问了几次（0次=刚切入，1次=追问过一次，≥2次=已追问够了）
D. 候选人情绪：自信 / 正常 / 犹豫 / 焦虑 / 疲惫

▶ 【第二步：按优先级匹配决策规则，执行优先级最高的那条】

🔴 P0（最高优先级）— 必须换话题的情况：
  ✦ 回答与问题完全无关（答非所问）→ 换话题，新话题从入门级问题开始
  ✦ 该话题已连续追问 ≥2 次，且回答质量未达到"优秀" → 换话题，难度归零
  ✦ 候选人明确表示不了解/不知道 → 换话题，加一句简短鼓励

🟡 P1（开场阶段规则，第1-2轮）— 暖场优先于一切技术考察：
  ✦ 第1轮：必须用开放式引导问题，请候选人介绍最近参与的一个项目或印象深刻的技术经历
           （禁止：考察名词概念、算法题、系统设计题）
  ✦ 第2轮：基于候选人第1轮分享的具体项目/经历，追问其中遇到的难题或挑战

🟢 P2（正常追问规则）— 在未触发P0且不在P1阶段时执行：
  ✦ 回答质量=优秀 且 该话题追问次数=0 → 在当前话题内适度加深难度（原理/边界/优化）
  ✦ 回答质量=基本正确/有缺漏 且 该话题追问次数=0 → 针对缺漏点追问一次
  ✦ 回答质量=基本正确/有缺漏 且 该话题追问次数=1 → 换话题，新话题从简单开始
  ✦ 情绪=焦虑/疲惫 → 切换轻松话题，加一句鼓励，降低难度

🔵 P3（轮次阶段规划，在P0/P1/P2均未触发时参考）：
  ✦ 第3-5轮：技术基础（每换话题先问基础概念，再逐步加深）
  ✦ 第6-8轮：技术深度 + 项目细节（追问技术选型/踩坑/优化）
  ✦ 第9轮+：系统设计 / 最薄弱维度 / 开放性综合题

▶ 【第三步：换话题时的难度重置规则】
  - 每当切换新话题，该话题第一个问题必须是入门级/开放性问题，不得直接出高难度题
  - 例：从"Redis 原理"换到"并发编程" → 先问"你在项目里用过多线程吗？介绍一下场景"
  - 参考知识库中的技术考点可作为话题候选，但切入方式要从简单开始

请直接输出下一个面试问题（50-150字），不要输出任何分析过程或前缀说明。"""

PROMPT_EVALUATE_ANSWER = """你是专业的 AI 面试官，请对候选人的单次回答进行快速深度评估。
要求：基于给定题目与回答做事实性判断，简洁客观；不得臆造候选人未表述的内容。

岗位：{position}
面试题目：{question}
候选人回答：
{answer}

请从以下 5 个维度评估（每项 0-10 分）：
1. 技术准确性：概念是否正确、有无技术错误
2. 知识深度：是否理解底层原理，而非停留表面
3. 逻辑严谨性：回答是否有条理、推理是否严密
4. 岗位匹配度：回答是否切合「{position}」岗位实际需求
5. 表达清晰度：语言是否简洁清晰、结构化

请返回严格 JSON（不要 markdown 包裹）：
{{
    "technical_score": 8,
    "depth_score": 7,
    "logic_score": 7,
    "job_match_score": 8,
    "clarity_score": 7,
    "overall": 7.5,
    "highlight": "一句话亮点",
    "weakness": "一句话不足",
    "tip": "一句话具体改进建议"
}}"""

PROMPT_FINAL_REPORT = """你是专业的 AI 面试评估专家，请根据以下【完整面试对话记录】，对候选人进行客观、差异化的多维量化评估。
本任务面向长文本结构化输出：逐条引用对话事实，条理清晰。

⚠️ 重要原则：
- 评分必须完全基于对话内容，绝不能使用预设的默认值
- 不同面试表现的评分应有显著差异：优秀候选人可得 8.5-10 分，普通表现 6-7.5 分，较差表现可低至 3-5 分
- 每个维度的分数都应反映候选人在该维度的真实水平，不同维度之间也应有明显区分
- 若对话记录非常短或候选人回答质量极差，overall_score 可以低至 3-5 分，请如实评估

岗位：{position}
难度：{difficulty}
完整面试记录：
{conversation}

═══════════════ 评估维度（0-10 分，须逐项独立打分）═══════════════

【技术 / 认知】
1. technical_correctness_score（技术正确性）：事实与概念是否准确，有无明显错误
2. knowledge_depth_score（知识深度）：是否触及原理、边界与权衡，而非仅背概念
3. logic_score（逻辑严谨性）：推理链条是否完整、条理是否清楚
4. job_match_score（岗位匹配度）：与「{position}」典型工作场景、技能栈的契合度

【综合软技能】
5. communication_score（沟通表达）：结构化表达、信息密度、是否答非所问
6. adaptability_score（应变能力）：对追问、变式问题的调整与补充能力

【表达呈现】
7. speech_rate_score（语速与流畅）：节奏、停顿与填充词（文本面试可从篇幅与连贯性推断）
8. clarity_score（表达清晰度）：是否易懂、层次分明
9. confidence_score（自信度）：表述是否迟疑、过度模糊
10. expression_score（综合表达）：以上表达维度的整体印象

【兼容字段】
11. content_score：填 (technical_correctness_score + knowledge_depth_score) / 2 的数值，保留1位小数，供旧版统计兼容

综合评分 overall_score（保留1位小数）请按下式计算（与上列分数一致）：
overall_score =
  technical_correctness_score×0.12 + knowledge_depth_score×0.12 + logic_score×0.12 + job_match_score×0.10
  + communication_score×0.12 + adaptability_score×0.10 + speech_rate_score×0.05
  + clarity_score×0.09 + confidence_score×0.08 + expression_score×0.10

═══════════════ 输出要求 ═══════════════

亮点（highlights）：4-6 条【具体】优点，引用对话事实，动词开头
不足（weaknesses）：3-5 条【具体】不足，指出轮次/事实与影响
改进建议（suggestions）：5-8 条【可操作】建议（学习主题、练习方式、复盘清单）

improvement_resources（结构化提升资源，须基于对话与岗位真实生成，勿编造不存在的书名）：
- knowledge_points：3-6 条，每条含 topic（知识点名称）、summary（为何重要）、action（如何补：文档/实验/复盘）
- sample_interview_questions：3-5 条，每条含 question（高频或进阶题）、focus（考察点）
- communication_readings：2-4 条，每条含 title（文章/主题名）、summary（1-2句要点）、url_or_search（真实可访问 URL；若无把握则填「检索：关键词」）

dimension_feedback：对象，键从以下中文维度中选择（有则填）：「技术正确性」「知识深度」「逻辑思维」「岗位匹配」「沟通表达」「应变能力」「表达清晰度」「自信度」「语速与流畅」「综合表达」。
每个值为：{{"comment": "50-120字", "evidence": "对话摘录或概括"}}

report_markdown：字符串（不要外层代码块），须含：
- ## 总体评价
- ## 分维度综述（### 小标题）
- 表格 | 维度 | 得分(0-10) | 依据 |（得分与 JSON 完全一致，维度含：技术正确性、知识深度、逻辑严谨性、岗位匹配、沟通表达、应变能力、语速与流畅、表达清晰度、自信度、综合表达）
- ## 能力雷达解读
- ## 后续提升路径（1周内 / 1个月内）
可选 mermaid 流程图（≤8 节点）。勿重复粘贴整段 JSON。

请直接返回如下 JSON（不要 markdown 代码块、不要额外说明）：
{{
    "overall_score": 0.0,
    "technical_correctness_score": 0,
    "knowledge_depth_score": 0,
    "logic_score": 0,
    "job_match_score": 0,
    "communication_score": 0,
    "adaptability_score": 0,
    "speech_rate_score": 0,
    "clarity_score": 0,
    "confidence_score": 0,
    "expression_score": 0,
    "content_score": 0,
    "highlights": [],
    "weaknesses": [],
    "suggestions": [],
    "improvement_resources": {{
        "knowledge_points": [{{"topic": "", "summary": "", "action": ""}}],
        "sample_interview_questions": [{{"question": "", "focus": ""}}],
        "communication_readings": [{{"title": "", "summary": "", "url_or_search": ""}}]
    }},
    "dimension_feedback": {{}},
    "report_markdown": ""
}}"""

PROMPT_RESUME_ANALYSIS = """你是专业的简历解析助手（可处理 OCR/文本），需从简历中提取结构化信息。
仅输出 JSON，无 markdown、无解释性正文。字段以原文为准，不得臆造。

请仔细阅读以下简历内容，并提取关键信息：

简历内容：
{resume_text}

请按以下 JSON 格式返回提取的信息：
{{
    "basic_info": {{
        "name": "姓名",
        "email": "邮箱",
        "phone": "手机号",
        "gender": "性别（如有）",
        "years_of_experience": "工作年限（数字）"
    }},
    "education": [
        {{
            "school": "学校名称",
            "degree": "学历（本科/硕士/博士等）",
            "major": "专业",
            "start_date": "开始时间",
            "end_date": "结束时间"
        }}
    ],
    "experience": [
        {{
            "company": "公司名称",
            "position": "职位",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "achievements": "主要成就和职责描述"
        }}
    ],
    "projects": [
        {{
            "name": "项目名称",
            "role": "担任角色",
            "description": "项目描述"
        }}
    ],
    "skills": ["技能1", "技能2"]
}}

要求：
1. 准确提取原文中的信息，不要臆造
2. 如果某项信息不存在，对应字段设为 null 或空数组
3. 直接返回 JSON 对象，不要有其他说明文字"""

PROMPT_RESUME_OPTIMIZE = """你是专业的简历优化专家，请对以下简历内容进行全面优化，使其更加专业、有竞争力。

原始简历数据：
{resume_data}

优化要求：
1. 【工作经历】每条成就严格遵循 STAR 法则，必须量化结果（如"将页面加载速度提升 40%"、"独立完成功能模块开发，覆盖 XX 用户"），动词开头，言简意赅
2. 【项目经验】强调技术选型、解决的核心难题和个人贡献度，体现技术深度
3. 【技能清单】按类别归组（如：前端框架、后端技术、数据库、工具链等），突出核心竞争力
4. 【措辞优化】替换模糊词汇（"参与"→"主导/负责/独立实现"），突出主动性和影响力
5. 【信息完整性】如原始信息较少，可适当补全合理的占位内容（标注"请补充"）

优化原则：
- 保持真实性，不无中生有
- 使用行业关键词和专业术语
- 语言简洁有力，每条不超过 80 字

请严格按以下 JSON 格式返回，注意 achievements 必须是字符串数组（每条一个字符串）：
{{
    "basic_info": {{"name": "姓名", "email": "邮箱", "phone": "手机号"}},
    "education": [{{"school": "", "degree": "", "major": "", "start_date": "", "end_date": "", "honors": ""}}],
    "experience": [{{"company": "", "position": "", "start_date": "", "end_date": "", "achievements": ["优化后成就条目1", "优化后成就条目2"]}}],
    "projects": [{{"name": "", "role": "", "description": ""}}],
    "skills": ["技能1", "技能2"]
}}

直接返回 JSON 对象，不要有任何 markdown 代码块或其他说明文字。"""


# ==================== LangChain LLM 客户端缓存 ====================
# key: (model_name, streaming) → ChatOpenAI 实例
# 避免每次调用都新建 httpx 连接池
_llm_cache: Dict[Tuple[str, bool], ChatOpenAI] = {}


def _build_llm(streaming: bool = False, model: Optional[str] = None) -> ChatOpenAI:
    """
    返回缓存的 ChatOpenAI 实例。
    相同 (model, streaming) 组合只创建一次，后续复用同一连接池。

    Args:
        streaming: 是否启用流式输出
        model:     指定模型名称，None 时使用 DASHSCOPE_MODEL
    """
    if not _api_key_ok:
        raise RuntimeError(
            "DASHSCOPE_API_KEY 未配置！请在 backend/.env 中填写阿里云百炼 API Key。\n"
            "获取地址：https://bailian.console.aliyun.com/"
        )

    _model = model or DASHSCOPE_MODEL
    key = (_model, streaming)

    if key not in _llm_cache:
        _llm_cache[key] = ChatOpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            model=_model,
            temperature=0.7,
            timeout=DASHSCOPE_TIMEOUT,
            streaming=streaming,
            max_retries=2,
        )

    return _llm_cache[key]


# ==================== 核心 API：非流式调用 ====================

async def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    调用 DashScope LLM（非流式），等待完整响应后返回。

    Args:
        prompt:        用户侧提示词
        system_prompt: 系统角色提示词，None 时使用默认面试官提示词
        model:         指定模型（None 则用 DASHSCOPE_MODEL），可传入
                       MODEL_INTERVIEW / MODEL_REPORT / MODEL_RESUME_VL 等常量

    Returns:
        AI 回复的完整文本
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT_INTERVIEWER

    _model = model or DASHSCOPE_MODEL
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    try:
        llm = _build_llm(streaming=False, model=_model)
        response = await llm.ainvoke(messages)
        content = response.content
        # 全局兜底：空响应时避免上层崩溃
        if content is None or (isinstance(content, str) and not content.strip()):
            return "（模型未返回有效文本，请检查网络、模型名与配额；可稍后重试或联系管理员。）"
        return content
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[LLM] 非流式调用失败：{e}")
        raise Exception(f"LLM 调用失败：{e}") from e


# ==================== 核心 API：流式调用 ====================

async def call_llm_stream(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    调用 DashScope LLM（流式），逐 token 异步生成响应。

    Args:
        prompt:        用户侧提示词
        system_prompt: 系统角色提示词，None 时使用默认面试官提示词
        model:         指定模型，None 则用 MODEL_INTERVIEW

    Yields:
        每次 yield 返回一个文本片段（chunk）
    """
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT_INTERVIEWER

    _model = model or MODEL_INTERVIEW
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    try:
        llm = _build_llm(streaming=True, model=_model)
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield chunk.content
    except RuntimeError:
        raise
    except Exception as e:
        logger.error(f"[LLM] 流式调用失败：{e}")
        raise Exception(f"LLM 流式调用失败：{e}") from e
