import logging
from typing import Optional

from config.cache_conf import get_cache, set_cache, delete_cache

logger = logging.getLogger(__name__)

# Token 缓存 key 前缀，格式：token:{token_value} → user_id
_TOKEN_PREFIX = "token:"
# 默认与数据库 Token 有效期一致（7 天），实际写入时会按剩余有效期设置
_TOKEN_DEFAULT_TTL = 7 * 24 * 3600


async def get_cached_user_id_by_token(token: str) -> Optional[int]:
    """
    从 Redis 缓存中获取 Token 对应的 user_id。

    Returns:
        user_id (int) 或 None（缓存未命中 / Redis 异常）
    """
    raw = await get_cache(f"{_TOKEN_PREFIX}{token}")
    if raw:
        logger.debug("[Cache] Token 缓存命中")
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None
    return None


async def cache_user_token(token: str, user_id: int, ttl: int = _TOKEN_DEFAULT_TTL) -> None:
    """
    将 Token → user_id 映射写入 Redis。

    Args:
        token:   用户 Token 字符串
        user_id: 对应的用户 ID
        ttl:     缓存有效期（秒），默认跟随 Token 剩余有效期
    """
    await set_cache(f"{_TOKEN_PREFIX}{token}", str(user_id), ttl)
    logger.debug(f"[Cache] Token 已缓存，user_id={user_id}，TTL={ttl}s")


async def invalidate_token(token: str) -> None:
    """
    从 Redis 删除 Token 缓存（如登出时调用）。
    """
    await delete_cache(f"{_TOKEN_PREFIX}{token}")
    logger.debug("[Cache] Token 缓存已删除")
