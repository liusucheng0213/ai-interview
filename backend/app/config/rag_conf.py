"""Chroma 子集合 + 本地向量或 DashScope Embedding；DashScope 失败时自动降级本地。"""
import asyncio
import logging
import os
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_DIMENSION = int(os.getenv("RAG_EMBEDDING_DIMENSION", "512"))
# 本地向量模型目录（仅当 RAG_USE_DASHSCOPE_EMBEDDING 未开启时使用）
EMBEDDING_MODEL_PATH = os.getenv(
    "RAG_LOCAL_EMBEDDING_MODEL_PATH",
    "./models_rag/bge-small-zh-v1.5",
)
CHROMA_DB_PATH = "./chroma_db"
CHILD_COLLECTION_NAME = os.getenv("CHROMA_CHILD_COLLECTION_NAME", "kb_child_chunks")
RAG_USE_DASHSCOPE_EMBEDDING: bool = os.getenv("RAG_USE_DASHSCOPE_EMBEDDING", "").lower() in (
    "1",
    "true",
    "yes",
)

embedding_model: Optional[SentenceTransformer] = None
chroma_client: Optional[chromadb.Client] = None
child_collection = None

__all__ = [
    "embedding_model",
    "child_collection",
    "CHILD_COLLECTION_NAME",
    "chroma_client",
    "init_rag",
    "close_rag",
    "initialize_embedding_model",
    "initialize_chroma_db",
]


def initialize_embedding_model() -> Optional[SentenceTransformer]:
    global embedding_model

    if not os.path.exists(EMBEDDING_MODEL_PATH):
        logger.error("嵌入模型路径不存在：%s", EMBEDDING_MODEL_PATH)
        return None

    try:
        embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH)
        embedding_model.encode("测试", convert_to_numpy=True)
        logger.info("嵌入模型加载成功，设备：%s", embedding_model.device)
        return embedding_model
    except Exception as e:
        logger.error("嵌入模型加载失败：%s", e)
        return None


def initialize_chroma_db() -> None:
    global chroma_client, child_collection

    logger.info("初始化 ChromaDB：%s", CHROMA_DB_PATH)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    for legacy in ("position_knowledge", "general_knowledge"):
        try:
            chroma_client.delete_collection(legacy)
            logger.info("已删除旧集合：%s", legacy)
        except Exception:
            pass

    child_collection = chroma_client.get_or_create_collection(
        name=CHILD_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    try:
        n = child_collection.count()
    except Exception:
        n = 0
    logger.info("子块集合 %s 就绪，文档数：%s", CHILD_COLLECTION_NAME, n)


def _create_probed_dashscope_wrapper():
    from services.kb.dashscope_embed import DashScopeEmbeddingWrapper

    w = DashScopeEmbeddingWrapper()
    w.encode("rag-init-probe", convert_to_numpy=True)
    return w


async def init_rag() -> None:
    global embedding_model, chroma_client, child_collection

    loop = asyncio.get_running_loop()
    logger.info("RAG 初始化（线程池）...")
    chroma_future = loop.run_in_executor(None, initialize_chroma_db)
    await chroma_future

    if RAG_USE_DASHSCOPE_EMBEDDING:
        try:
            embedding_model = await loop.run_in_executor(None, _create_probed_dashscope_wrapper)
            logger.info(
                "RAG 使用 DashScope 向量（%s），集合：%s",
                getattr(embedding_model, "model", "?"),
                CHILD_COLLECTION_NAME,
            )
        except Exception as e:
            logger.warning("DashScope 向量不可用，降级本地嵌入：%s", e)
            embedding_model = await loop.run_in_executor(None, initialize_embedding_model)
            if embedding_model is None:
                logger.warning("本地嵌入未加载，语义检索不可用")
            else:
                logger.info("RAG 已降级为本地嵌入模型")
    else:
        embedding_model = await loop.run_in_executor(None, initialize_embedding_model)
        if embedding_model is None:
            logger.warning("嵌入模型未加载，语义检索不可用")
        else:
            logger.info("RAG 本地嵌入模型加载完成")

    logger.info("RAG 初始化完成")


def close_rag() -> None:
    global embedding_model, chroma_client, child_collection
    embedding_model = None
    chroma_client = None
    child_collection = None
    logger.info("RAG 资源已释放")
