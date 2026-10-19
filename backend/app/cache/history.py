import logging
from typing import Optional

from config.cache_conf import get_cache, set_cache, delete_cache

logger = logging.getLogger(__name__)

# 当前进行中面试 ID 缓存，格式：current_interview:{user_id} → interview_id
_CURRENT_INTERVIEW_PREFIX = "current_interview:"
_CURRENT_INTERVIEW_TTL = 4 * 3600  # 4 小时，面试通常不会超过这个时长


async def get_current_interview_id(user_id: int) -> Optional[int]:
    """
    从 Redis 缓存获取用户当前进行中面试的 ID。

    Returns:
        interview_id (int) 或 None（缓存未命中 / Redis 异常）
    """
    raw = await get_cache(f"{_CURRENT_INTERVIEW_PREFIX}{user_id}")
    if raw:
        logger.debug(f"[Cache] 当前面试缓存命中，user_id={user_id}")
        try:
            return int(raw)
        except (ValueError, TypeError):
            return None
    return None


async def set_current_interview_id(user_id: int, interview_id: int) -> None:
    """
    将用户当前进行中面试的 ID 写入 Redis 缓存。
    """
    await set_cache(
        f"{_CURRENT_INTERVIEW_PREFIX}{user_id}",
        str(interview_id),
        _CURRENT_INTERVIEW_TTL,
    )
    logger.debug(f"[Cache] 当前面试已缓存，user_id={user_id}，interview_id={interview_id}")


async def invalidate_current_interview(user_id: int) -> None:
    """
    删除用户当前面试的缓存（面试结束或开始新面试时调用）。
    """
    await delete_cache(f"{_CURRENT_INTERVIEW_PREFIX}{user_id}")
    logger.debug(f"[Cache] 当前面试缓存已删除，user_id={user_id}")
