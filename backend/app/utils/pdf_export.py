"""
使用 reportlab 生成 PDF（面试报告、简历），优先注册系统中文字体。
"""
import io
import logging
import os
from typing import Any, Dict, List, Optional

from config.env_util import env_str

logger = logging.getLogger(__name__)

_FONT_REGISTERED = False
_CN_FONT = "Helvetica"


def _ensure_cn_font() -> str:
    global _FONT_REGISTERED, _CN_FONT
    if _FONT_REGISTERED:
        return _CN_FONT
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        env_path = env_str("PDF_CN_FONT", "")
        candidates = []
        if env_path and os.path.isfile(env_path):
            candidates.append(env_path)
        # 操作系统自带字体，不是某台电脑的用户目录。可用 PDF_CN_FONT 覆盖。
        candidates.extend(
            [
                r"C:\Windows\Fonts\msyh.ttc",
                r"C:\Windows\Fonts\simhei.ttf",
                r"C:\Windows\Fonts\simsun.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            ]
        )
        for path in candidates:
            if path and os.path.isfile(path):
                try:
                    pdfmetrics.registerFont(TTFont("CNFont", path))
                    _CN_FONT = "CNFont"
                    _FONT_REGISTERED = True
                    logger.info(f"[PDF] 已注册中文字体：{path}")
                    return _CN_FONT
                except Exception as e:
                    logger.debug(f"[PDF] 字体注册失败 {path}: {e}")
    except ImportError:
        logger.warning("[PDF] 未安装 reportlab，无法生成 PDF")
    _FONT_REGISTERED = True
    logger.warning("[PDF] 未找到可用的中文字体，PDF 中文可能显示为方框。可设置环境变量 PDF_CN_FONT。")
    return _CN_FONT


def interview_report_to_pdf(
    *,
    position_name: str,
    difficulty_label: str,
    mode_label: str,
    interview_round: int,
    total_score: float,
    highlights: List[str],
    weaknesses: List[str],
    suggestions: List[str],
    dimension_rows: List[tuple],
    improvement_resources: Optional[Dict[str, Any]] = None,
) -> io.BytesIO:
    """生成面试评估报告 PDF。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = _ensure_cn_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="TitleCN",
        parent=styles["Title"],
        fontName=font,
        fontSize=18,
        leading=24,
        alignment=1,
    )
    h2_style = ParagraphStyle(
        name="H2CN",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=13,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        name="BodyCN",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=14,
    )
    story = []
    story.append(Paragraph("AI 模拟面试评估报告", title_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"岗位：{position_name}　|　难度：{difficulty_label}　|　形式：{mode_label}",
            body_style,
        )
    )
    story.append(Spacer(1, 0.6 * cm))

    story.append(Paragraph("综合得分", h2_style))
    ts = float(total_score) if total_score is not None else 0.0
    story.append(Paragraph(f"<b>总分：{ts:.1f} / 10</b>", body_style))
    story.append(Spacer(1, 0.4 * cm))

    if dimension_rows:
        story.append(Paragraph("各维度得分", h2_style))
        data = [["维度", "得分"]] + [[a, f"{float(b):.1f}"] for a, b in dimension_rows]
        t = Table(data, colWidths=[10 * cm, 4 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), font, 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 0.5 * cm))

    def _bullets(title: str, items: List[str], color_hex: str):
        story.append(Paragraph(title, ParagraphStyle(name="hx", parent=h2_style, textColor=colors.HexColor(color_hex))))
        if not items:
            story.append(Paragraph("（暂无）", body_style))
            return
        for it in items:
            story.append(Paragraph(f"• {str(it)}", body_style))

    _bullets("亮点表现", highlights, "#16a34a")
    story.append(Spacer(1, 0.35 * cm))
    _bullets("不足之处", weaknesses, "#d97706")
    story.append(Spacer(1, 0.35 * cm))
    _bullets("改进建议", suggestions, "#2563eb")

    ir = improvement_resources if isinstance(improvement_resources, dict) else {}
    kp = ir.get("knowledge_points") or []
    siq = ir.get("sample_interview_questions") or []
    cr = ir.get("communication_readings") or []
    if isinstance(kp, list) and kp:
        story.append(Spacer(1, 0.35 * cm))
        items = []
        for it in kp[:10]:
            if not isinstance(it, dict):
                continue
            line = f"{it.get('topic', '')}：{it.get('summary', '')}（行动：{it.get('action', '')}）"
            items.append(line.strip("："))
        _bullets("巩固知识点", items, "#0d9488")
    if isinstance(siq, list) and siq:
        story.append(Spacer(1, 0.35 * cm))
        items = []
        for it in siq[:10]:
            if not isinstance(it, dict):
                continue
            items.append(f"{it.get('question', '')} — 考察：{it.get('focus', '')}")
        _bullets("常见 / 进阶面试题", items, "#7c3aed")
    if isinstance(cr, list) and cr:
        story.append(Spacer(1, 0.35 * cm))
        items = []
        for it in cr[:8]:
            if not isinstance(it, dict):
                continue
            url = it.get("url_or_search") or it.get("url") or ""
            items.append(f"{it.get('title', '')}：{it.get('summary', '')} ({url})")
        _bullets("沟通与表达延伸阅读", items, "#0369a1")

    doc.build(story)
    buf.seek(0)
    return buf


def resume_data_to_pdf(resume_data: Dict[str, Any]) -> io.BytesIO:
    """由结构化简历数据生成 PDF（与 Word 版信息层次相近）。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font = _ensure_cn_font()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        name="ResumeName",
        parent=styles["Title"],
        fontName=font,
        fontSize=22,
        alignment=1,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        name="ResumeSub",
        parent=styles["Normal"],
        fontName=font,
        fontSize=9.5,
        alignment=1,
        textColor=colors.HexColor("#64748b"),
    )
    sec_style = ParagraphStyle(
        name="Sec",
        parent=styles["Heading2"],
        fontName=font,
        fontSize=12,
        textColor=colors.HexColor("#1e40af"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        name="RB",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        leading=14,
    )

    story = []
    basic = resume_data.get("basic_info") or {}
    name = basic.get("name") or "简历"
    story.append(Paragraph(name, name_style))
    bits = []
    if basic.get("email"):
        bits.append(f"邮箱：{basic['email']}")
    if basic.get("phone"):
        bits.append(f"电话：{basic['phone']}")
    if basic.get("job_target"):
        bits.append(f"求职意向：{basic['job_target']}")
    if bits:
        story.append(Paragraph("　·　".join(bits), sub_style))
    story.append(Spacer(1, 0.5 * cm))

    def esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    edu = resume_data.get("education") or []
    if edu:
        story.append(Paragraph("教育背景", sec_style))
        for e in edu:
            if not isinstance(e, dict):
                continue
            line = f"<b>{esc(e.get('school', ''))}</b>　{esc(e.get('degree', ''))} · {esc(e.get('major', ''))}"
            story.append(Paragraph(line, body))
            story.append(
                Paragraph(
                    f"{esc(e.get('start_date', ''))} — {esc(e.get('end_date', '至今'))}",
                    body,
                )
            )
            if e.get("honors"):
                story.append(Paragraph(f"荣誉：{esc(str(e['honors']))}", body))
            story.append(Spacer(1, 0.2 * cm))

    exp = resume_data.get("experience") or []
    if exp:
        story.append(Paragraph("工作经历", sec_style))
        for e in exp:
            if not isinstance(e, dict):
                continue
            story.append(Paragraph(f"<b>{esc(e.get('company', ''))}</b>　{esc(e.get('position', ''))}", body))
            story.append(
                Paragraph(
                    f"{esc(e.get('start_date', ''))} — {esc(e.get('end_date', '至今'))}",
                    body,
                )
            )
            ach = e.get("achievements")
            if isinstance(ach, list):
                for a in ach:
                    if a:
                        story.append(Paragraph(f"• {esc(str(a))}", body))
            elif ach:
                story.append(Paragraph(f"• {esc(str(ach))}", body))
            story.append(Spacer(1, 0.25 * cm))

    proj = resume_data.get("projects") or []
    if proj:
        story.append(Paragraph("项目经验", sec_style))
        for p in proj:
            if not isinstance(p, dict):
                continue
            role = f"（{p.get('role', '')}）" if p.get("role") else ""
            story.append(Paragraph(f"<b>{esc(p.get('name', ''))}</b>{esc(role)}", body))
            if p.get("description"):
                story.append(Paragraph(esc(str(p["description"])), body))
            story.append(Spacer(1, 0.25 * cm))

    skills = resume_data.get("skills") or []
    if skills:
        story.append(Paragraph("技能清单", sec_style))
        txt = "、".join(skills) if isinstance(skills, list) else str(skills)
        story.append(Paragraph(esc(txt), body))

    doc.build(story)
    buf.seek(0)
    return buf
