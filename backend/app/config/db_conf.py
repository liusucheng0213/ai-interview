import logging

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config.env_util import env_int, env_str

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 数据库连接URL
MYSQL_USER = env_str("MYSQL_USER", "root")
# 请配置 MYSQL_PASSWORD，获取方式：MySQL 安装时为本账户设置的密码，或云数据库控制台的账号页面
MYSQL_PASSWORD = env_str("MYSQL_PASSWORD", "")
MYSQL_HOST = env_str("MYSQL_HOST", "localhost")
MYSQL_PORT = env_int("MYSQL_PORT", 3306)
MYSQL_DB = env_str("MYSQL_DB", "test_db")
MYSQL_URL = URL.create(
    "mysql+aiomysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DB,
)
MYSQL_POOL_SIZE = env_int("MYSQL_POOL_SIZE", 20)
MYSQL_MAX_OVERFLOW = env_int("MYSQL_MAX_OVERFLOW", 30)
MYSQL_POOL_RECYCLE = env_int("MYSQL_POOL_RECYCLE", 3600)
MYSQL_POOL_TIMEOUT = env_int("MYSQL_POOL_TIMEOUT", 30)

# 创建异步引擎（生产环境关闭echo）
async_engine = create_async_engine(
    MYSQL_URL,
    pool_size=MYSQL_POOL_SIZE,
    max_overflow=MYSQL_MAX_OVERFLOW,
    echo=False,  # 必须关闭！避免日志干扰+性能问题
    pool_recycle=MYSQL_POOL_RECYCLE,  # 连接回收，避免超时断链
    pool_timeout=MYSQL_POOL_TIMEOUT,
    pool_pre_ping=True,
)

# 创建异步会话工厂（核心：移除async with，改用手动创建）
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


# 异步依赖：手动创建/关闭会话（FastAPI官方推荐写法）
async def get_db():
    """
    修复greenlet错误的核心：不用async with，手动管理会话生命周期
    """
    async with AsyncSessionLocal() as db:  # 直接创建会话，而非async with
        try:
            yield db
            # 统一成功路径 commit：不改为「无脏数据则 rollback」，避免 Core 层 execute(update/insert)
            # 未反映到 session.dirty 时误 rollback 导致静默丢更新。
            await db.commit()
        except HTTPException:
            # 业务 HTTP 异常不应作为数据库错误记录
            await db.rollback()
            raise
        except Exception as e:
            logger.error(f"数据库会话异常：{str(e)}", exc_info=True)
            await db.rollback()  # 仅异常时回滚
            raise
        finally:
            await db.close()  # 手动关闭


