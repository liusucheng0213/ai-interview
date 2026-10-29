from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from config.env_util import env_str
from config.logger_conf import setup_logging, logging

setup_logging()
logger = logging.getLogger(__name__)

from config.cache_conf import init_redis, close_redis
from sqlalchemy import text

from config.db_conf import async_engine
from config.rag_conf import init_rag, close_rag
from models.base import Base
import models.rag_schema  # noqa: F401
from routers import users, interview, questions, resume, knowledge, company, rag, job
from utils.register_exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN enterprise_kf_disabled_json TEXT"))
            logger.info("已添加列 users.enterprise_kf_disabled_json")
        except Exception as e:
            # 列已存在或权限/语法等：不影响启动，仅记录便于排查
            logger.debug("跳过 users.enterprise_kf_disabled_json ALTER（多为列已存在）：%s", e)
    logger.info("数据库表初始化完成")

    try:
        await init_redis()
    except Exception as e:
        logger.warning("Redis 连接失败：%s", e)

    try:
        await init_rag()
    except Exception as e:
        logger.warning("RAG 初始化失败：%s", e)

    yield

    await async_engine.dispose()
    try:
        await close_redis()
    except Exception:
        pass
    close_rag()
    logger.info("应用已关闭")


app = FastAPI(
    title="AI 模拟面试系统",
    description="基于大模型和 RAG 的智能面试系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

cors_origins_raw = env_str("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(users.router)
app.include_router(interview.router)
app.include_router(questions.router)
app.include_router(resume.router)
app.include_router(knowledge.router)
app.include_router(company.router)
app.include_router(rag.router)
app.include_router(job.router)
