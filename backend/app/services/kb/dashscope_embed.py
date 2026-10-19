"""
DashScope 文本向量（如 text-embedding-v3），用于 RAG 检索。
与本地 SentenceTransformer 二选一；切换后需使用新的 Chroma 集合并重新向量化。
"""
from __future__ import annotations

import logging
import os
from typing import List, Sequence, Union

import httpx
import numpy as np

logger = logging.getLogger(__name__)

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_EMBEDDING_MODEL = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")
_EMBED_TIMEOUT = float(os.getenv("DASHSCOPE_EMBEDDING_TIMEOUT", "60"))


class DashScopeEmbeddingWrapper:
    """
    与 SentenceTransformer.encode 类似的轻量封装，供 chroma_child 使用。
    encode 接受 str 或 str 列表，返回 numpy.ndarray，shape (n, dim)。
    """

    def __init__(self, model: str | None = None):
        self.model = model or DASHSCOPE_EMBEDDING_MODEL
        self._dim: int | None = None

    @property
    def device(self) -> str:
        return "dashscope-api"

    def encode(
        self,
        texts: Union[str, Sequence[str]],
        convert_to_numpy: bool = True,
        batch_size: int = 16,
        **kwargs,
    ):
        if isinstance(texts, str):
            inputs: List[str] = [texts]
        else:
            inputs = [t if isinstance(t, str) else str(t) for t in texts]
        if not inputs:
            return np.array([])

        url = f"{DASHSCOPE_BASE_URL.rstrip('/')}/embeddings"
        all_rows: List[List[float]] = []
        # DashScope embedding 接口单次 input 最多 10 条，统一在这里兜底截断批大小。
        safe_batch_size = max(1, min(int(batch_size or 10), 10))

        try:
            with httpx.Client(timeout=_EMBED_TIMEOUT) as client:
                for i in range(0, len(inputs), safe_batch_size):
                    chunk = inputs[i : i + safe_batch_size]
                    body = {"model": self.model, "input": chunk, "encoding_format": "float"}
                    resp = client.post(
                        url,
                        headers={
                            "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                    if resp.status_code != 200:
                        logger.error(
                            "[DashScope-Embed] HTTP %s: %s",
                            resp.status_code,
                            resp.text[:500],
                        )
                        raise RuntimeError(f"Embedding API 失败：HTTP {resp.status_code}")
                    data = resp.json()
                    items = data.get("data") or []
                    # 保持与请求 chunk 顺序一致
                    sorted_items = sorted(items, key=lambda x: x.get("index", 0))
                    if len(sorted_items) != len(chunk):
                        raise RuntimeError(
                            f"Embedding 数量不一致：请求 {len(chunk)} 条，返回 {len(sorted_items)} 条"
                        )
                    for it in sorted_items:
                        emb = it.get("embedding")
                        if not emb:
                            raise RuntimeError("Embedding 响应缺少 embedding 字段")
                        all_rows.append(emb)
                        if self._dim is None:
                            self._dim = len(emb)
        except Exception as e:
            logger.exception("[DashScope-Embed] 请求异常：%s", e)
            raise

        arr = np.array(all_rows, dtype=np.float32)
        if not convert_to_numpy:
            return arr.tolist()
        return arr
