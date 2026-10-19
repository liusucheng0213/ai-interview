"""
Chroma 子块集合：仅存储子块向量；metadata 含 chunk_id/parent_id/file_id（均为字符串）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

import config.rag_conf as rag_conf

logger = logging.getLogger(__name__)


def add_child_embeddings(
    items: List[Dict[str, Any]],
) -> None:
    """
    items: [{ "chroma_id", "content", "chunk_id", "parent_id", "file_id",
 "owner_user_id", "visibility", "org_id" }]
    """
    col = rag_conf.child_collection
    embed_model = rag_conf.embedding_model
    if col is None:
        raise RuntimeError("child_collection 未初始化")

    ids = [x["chroma_id"] for x in items]
    docs = [x["content"] for x in items]
    metas = [
        {
            "chunk_id": str(x["chunk_id"]),
            "parent_id": str(x["parent_id"]),
            "file_id": str(x["file_id"]),
            "owner_user_id": str(x.get("owner_user_id") or ""),
            "visibility": str(x.get("visibility") or "user_local"),
            "org_id": str(x.get("org_id") or ""),
        }
        for x in items
    ]

    if embed_model is not None:
        emb = embed_model.encode(docs).tolist()
        col.add(ids=ids, embeddings=emb, documents=docs, metadatas=metas)
    else:
        col.add(ids=ids, documents=docs, metadatas=metas)

    logger.info(f"[RAG v2] 写入 Chroma 子块 {len(ids)} 条")


def delete_children_by_chroma_ids(chroma_ids: List[str]) -> None:
    col = rag_conf.child_collection
    if col is None or not chroma_ids:
        return
    try:
        col.delete(ids=chroma_ids)
    except Exception as e:
        logger.warning(f"[RAG v2] 删除 Chroma 子块失败: {e}")


def delete_children_by_file_id(file_id: int) -> None:
    col = rag_conf.child_collection
    if col is None:
        return
    try:
        col.delete(where={"file_id": str(file_id)})
    except Exception as e:
        logger.warning(f"[RAG v2] 按 file_id 删除 Chroma 失败: {e}")


def query_children(
    query: str,
    top_k: int,
    file_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    col = rag_conf.child_collection
    embed_model = rag_conf.embedding_model
    if col is None or embed_model is None:
        return []
    try:
        if col.count() == 0:
            return []
    except Exception:
        return []

    q_emb = embed_model.encode([query]).tolist()
    n = col.count()
    n_results = min(max(top_k * 4, top_k), max(n, 1))
    where = {"file_id": str(file_id)} if file_id is not None else None
    raw = col.query(
        query_embeddings=q_emb,
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]
    out = []
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({"document": doc, "metadata": meta or {}, "distance": dist})
    return out
