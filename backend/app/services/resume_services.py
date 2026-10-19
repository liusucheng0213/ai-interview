"""
简历服务层 - 代理到 LLM_services 中的简历分析/优化功能

resume.py 路由通过 `from services.resume_services import analyze_resume, optimize_resume`
调用此模块，这里直接转发到统一的 LLM_services 实现。
"""

from services.LLM_services import analyze_resume, optimize_resume

__all__ = ["analyze_resume", "optimize_resume"]
