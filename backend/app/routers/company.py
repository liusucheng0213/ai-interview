import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from crud.history import (
    build_interview_detail_payload,
    get_evaluation_report_by_id,
    get_interview_by_id,
)
from models.history import InterviewRecordHistory, EvaluationReportHistory
from models.users import User
from utils.auth import get_current_user
from utils.security import get_hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/company", tags=["company"])

# 企业端重置密码的最短长度（字符）
MIN_RESET_PASSWORD_LENGTH = 6


def _ensure_enterprise(user: User) -> None:
    if getattr(user, "account_type", "personal") != "enterprise":
        raise HTTPException(status_code=403, detail="仅企业账号可访问")


@router.get("/users", summary="企业端：获取用户列表")
async def list_users(
    keyword: str = "",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_enterprise(user)
    stmt = select(User).order_by(User.credited_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    rows = []
    kw = (keyword or "").strip().lower()
    for u in users:
        if kw and kw not in (u.username or "").lower() and kw not in (u.email or "").lower():
            continue
        rows.append({
            "id": u.id,
            "username": u.username,
            "account_type": getattr(u, "account_type", "personal"),
            "created_at": str(u.credited_at) if getattr(u, "credited_at", None) else "",
        })
    return {"users": rows, "total": len(rows)}


@router.get("/interviews", summary="企业端：查询用户面试记录")
async def list_user_interviews(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_enterprise(user)
    stmt = select(InterviewRecordHistory).order_by(InterviewRecordHistory.credited_at.desc())
    if user_id:
        stmt = stmt.where(InterviewRecordHistory.user_id == user_id)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = []
    for r in rows:
        report_res = await db.execute(
            select(EvaluationReportHistory).where(EvaluationReportHistory.interview_id == r.id)
        )
        report = report_res.scalar_one_or_none()
        user_res = await db.execute(select(User).where(User.id == r.user_id))
        owner = user_res.scalar_one_or_none()
        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "username": owner.username if owner else f"用户{r.user_id}",
            "job": r.position_name,
            "difficulty": r.difficulty,
            "mode": r.mode,
            "status": r.interview_status,
            "round": r.interview_round,
            "score": report.total_score if report else None,
            "time": str(r.credited_at) if getattr(r, "credited_at", None) else "",
        })
    return {"interviews": items, "total": len(items)}


@router.get("/interviews/{interview_id}", summary="企业端：单条面试详情（与求职者测评报告一致）")
async def get_company_interview_detail(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回结构与 GET /api/interview/detail/{id} 相同，供企业管理台展示完整报告。"""
    _ensure_enterprise(user)
    history = await get_interview_by_id(interview_id, db)
    if not history:
        raise HTTPException(status_code=404, detail="面试记录不存在")
    report = await get_evaluation_report_by_id(interview_id, db)
    interview_data = build_interview_detail_payload(history, report)
    return {"interview": interview_data}


@router.put("/users/{target_user_id}/password", summary="企业端：重置用户密码")
async def reset_user_password(
    target_user_id: int,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_enterprise(user)
    if not new_password or len(new_password) < MIN_RESET_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"新密码长度至少 {MIN_RESET_PASSWORD_LENGTH} 位",
        )

    target = await db.get(User, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不允许重置当前企业账号自己的密码")

    hashed = get_hash_password(new_password)
    await db.execute(update(User).where(User.id == target_user_id).values(password=hashed))
    await db.commit()
    return {"message": "密码重置成功"}
