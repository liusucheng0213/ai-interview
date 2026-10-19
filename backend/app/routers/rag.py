from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_conf import get_db
from services.kb.rag_plan1 import retrieve_context
from utils.response import success_response

router = APIRouter(prefix="/api/rag", tags=["rag"])


class RetrieveFilterModel(BaseModel):
    chunk_type: Optional[str] = Field(default=None, description="job/question/resume/other")
    job_id: Optional[str] = Field(default=None, description="岗位ID，可选")


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户查询或面试题关键词")
    filter: Optional[RetrieveFilterModel] = None


class RetrieveChunk(BaseModel):
    chunk_id: str
    chunk_type: str
    content: str
    parent_id: Optional[str] = None
    score: float


class RetrieveResponse(BaseModel):
    context: str
    chunks: List[RetrieveChunk]
    retrieve_time: float


@router.post("/retrieve", summary="RAG 检索接口")
async def rag_retrieve(
    body: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")
    try:
        result = await retrieve_context(
            db=db,
            query=body.query.strip(),
            filter_data=body.filter.model_dump() if body.filter else None,
        )
        # 确保响应结构稳定
        payload = RetrieveResponse(
            context=result.get("context", ""),
            chunks=[RetrieveChunk(**c) for c in result.get("chunks", [])],
            retrieve_time=float(result.get("retrieve_time", 0.0)),
        )
        return success_response(message="ok", data=payload.model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 检索失败: {e}") from e
