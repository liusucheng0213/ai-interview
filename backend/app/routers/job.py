from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from models.rag_schema import Job
from services.kb.plan2_service import query_jobs_with_rag
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/job", tags=["job"])


class JobQueryRequest(BaseModel):
    keyword: str = Field(default="", description="岗位名称或关键词")
    with_question: bool = Field(default=False, description="是否返回关联题库与知识片段")


class JobUpsertRequest(BaseModel):
    job_name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="")
    tech_stack: dict | None = None


@router.post("/query", summary="岗位查询（支持关联题库）")
async def query_job_api(
    body: JobQueryRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        rows = await query_jobs_with_rag(
            db=db,
            keyword=body.keyword,
            with_question=body.with_question,
        )
        return success_response(message="ok", data={"jobs": rows, "total": len(rows)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"岗位查询失败: {e}") from e


@router.get("/list", summary="岗位列表")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    res = await db.execute(select(Job).order_by(Job.id.desc()))
    rows = res.scalars().all()
    return success_response(
        message="ok",
        data={
            "jobs": [
                {
                    "id": j.id,
                    "job_name": j.job_name,
                    "description": j.description,
                    "tech_stack": j.tech_stack,
                    "main_chunk_id": j.main_chunk_id,
                }
                for j in rows
            ]
        },
    )


@router.post("/create", summary="创建岗位")
async def create_job(
    body: JobUpsertRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    exists = await db.execute(select(Job).where(Job.job_name == body.job_name.strip()))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="岗位已存在")
    row = Job(job_name=body.job_name.strip(), description=body.description.strip(), tech_stack=body.tech_stack)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return success_response(message="ok", data={"id": row.id})


@router.put("/{job_id}", summary="更新岗位")
async def update_job(
    job_id: int,
    body: JobUpsertRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    res = await db.execute(select(Job).where(Job.id == job_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="岗位不存在")
    row.job_name = body.job_name.strip()
    row.description = body.description.strip()
    row.tech_stack = body.tech_stack
    await db.commit()
    return success_response(message="ok", data={"id": row.id})


@router.delete("/{job_id}", summary="删除岗位")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    res = await db.execute(select(Job).where(Job.id == job_id))
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="岗位不存在")
    await db.delete(row)
    await db.commit()
    return success_response(message="ok", data={"deleted": True})
