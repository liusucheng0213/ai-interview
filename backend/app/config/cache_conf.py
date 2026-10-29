import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from dotenv import load_dotenv

from config.env_util import env_int, env_str

load_dotenv()

logger = logging.getLogger(__name__)

# 连接池上限，供单进程本地开发使用
_REDIS_MAX_CONNECTIONS = 20
# 建连与读写超时（秒）
_REDIS_SOCKET_TIMEOUT_SECONDS = 10
# 调用方未传过期时间时，缓存保留 1 小时
_DEFAULT_CACHE_TTL_SECONDS = 3600

REDIS_HOST = env_str("REDIS_HOST", "localhost")
REDIS_PORT = env_int("REDIS_PORT", 6379)
REDIS_DB = env_int("REDIS_DB", 0)
# 请配置 REDIS_PASSWORD，获取方式：Redis 的 requirepass，或云厂商控制台；本地无密码请留空
REDIS_PASSWORD = env_str("REDIS_PASSWORD", "") or None

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """初始化 Redis 连接池，应在应用启动时调用。"""
    global _pool, _client
    _pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        max_connections=_REDIS_MAX_CONNECTIONS,
        socket_connect_timeout=_REDIS_SOCKET_TIMEOUT_SECONDS,
        socket_timeout=_REDIS_SOCKET_TIMEOUT_SECONDS,
        retry_on_timeout=True,
    )
    _client = redis.Redis(connection_pool=_pool)
    await _client.ping()
    logger.info(f"✅ Redis 连接成功：{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")


async def close_redis() -> None:
    """关闭 Redis 连接池，应在应用关闭时调用。"""
    global _pool, _client
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.aclose()
        _pool = None
    logger.info("Redis 连接已关闭")


def get_redis() -> redis.Redis:
    """获取 Redis 客户端实例。"""
    if _client is None:
        raise RuntimeError("Redis 未初始化，请先调用 init_redis()")
    return _client


async def get_cache(key: str) -> Optional[str]:
    """从 Redis 获取字符串值，缓存未命中或异常时返回 None。"""
    try:
        return await get_redis().get(key)
    except Exception as e:
        logger.warning(f"[Redis] get 失败，key={key}：{e}")
        return None


async def get_json_cache(key: str) -> Optional[Any]:
    """从 Redis 获取 JSON 值并反序列化，缓存未命中或异常时返回 None。"""
    try:
        raw = await get_redis().get(key)
        if raw:
            return json.loads(raw)
        return None
    except Exception as e:
        logger.warning(f"[Redis] get_json 失败，key={key}：{e}")
        return None


async def set_cache(key: str, value: str, expire: int = _DEFAULT_CACHE_TTL_SECONDS) -> bool:
    """将字符串值写入 Redis，并设置过期时间（秒）。"""
    try:
        await get_redis().setex(key, expire, value)
        return True
    except Exception as e:
        logger.warning(f"[Redis] set 失败，key={key}：{e}")
        return False


async def set_json_cache(key: str, value: Any, expire: int = _DEFAULT_CACHE_TTL_SECONDS) -> bool:
    """将可 JSON 序列化的值写入 Redis，并设置过期时间（秒）。"""
    try:
        serialized = json.dumps(value, ensure_ascii=False)
        await get_redis().setex(key, expire, serialized)
        return True
    except Exception as e:
        logger.warning(f"[Redis] set_json 失败，key={key}：{e}")
        return False


async def delete_cache(key: str) -> bool:
    """从 Redis 删除指定键。"""
    try:
        await get_redis().delete(key)
        return True
    except Exception as e:
        logger.warning(f"[Redis] delete 失败，key={key}：{e}")
        return False
