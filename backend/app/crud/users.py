import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cache.users import get_cached_user_id_by_token, cache_user_token
from models.users import User, UserToken
from schemas.users import UserRegisterRequest
from utils.security import get_hash_password, verify_password

logger = logging.getLogger(__name__)


async def get_user_by_username(db: AsyncSession, username: str):
    logger.info(f"🔍 从数据库查询用户 {username}")
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRegisterRequest):
    hashed_password = get_hash_password(user_data.password)

    db_user = User(
        username=user_data.username,
        password=hashed_password,
        email=user_data.email,
        gender="",
        major="",
        signature="",
        account_type=user_data.account_type if user_data.account_type in ("personal", "enterprise") else "personal",
        company_name=(user_data.company_name or "").strip() or None,
        company_code=(user_data.company_code or "").strip() or None,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    logger.info(f"✅ 用户创建成功：{user_data.username}")
    return db_user


async def create_or_update_token(db: AsyncSession, user_id: int):
    """生成或更新用户 Token，并同步写入 Redis 缓存。"""
    token = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(days=7)

    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    user_token = result.scalar_one_or_none()
    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
        user_token.updated_at = datetime.now()
        await db.commit()
        await db.refresh(user_token)
        logger.info(f"✅ 用户 Token 更新成功：user_id={user_id}")
    else:
        user_token = UserToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.add(user_token)
        await db.commit()
        await db.refresh(user_token)
        logger.info(f"✅ 用户 Token 生成成功：user_id={user_id}")

    ttl = int((expires_at - datetime.now()).total_seconds())
    await cache_user_token(token, user_id, ttl)

    return user_token.token


async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user:
        logger.info(f"用户 {username} 不存在")
        return None
    if not verify_password(password, user.password):
        logger.info(f"用户 {username} 密码错误")
        return None
    return user


async def get_user_by_token(db: AsyncSession, token: str):
    """根据 Token 查询用户：优先走 Redis 缓存，缓存未命中再查数据库。"""

    # 1. 先查 Redis 缓存（token → user_id）
    cached_user_id = await get_cached_user_id_by_token(token)
    if cached_user_id:
        result = await db.execute(select(User).where(User.id == cached_user_id))
        user_obj = result.scalar_one_or_none()
        if user_obj:
            logger.info(f"✅ [Cache] Token 命中，user_id={cached_user_id}")
            return user_obj
        # 缓存 user_id 对应用户不存在（异常情况），fall through

    # 2. 缓存未命中，查询数据库
    logger.info("🔍 从数据库查询用户 Token")
    result = await db.execute(select(UserToken).where(UserToken.token == token))
    db_token = result.scalar_one_or_none()
    if not db_token:
        logger.info("用户 Token 不存在")
        return None
    if db_token.expires_at < datetime.now():
        logger.info("用户 Token 已过期")
        return None

    user_result = await db.execute(select(User).where(User.id == db_token.user_id))
    user_obj = user_result.scalar_one_or_none()

    # 3. 将 token → user_id 写入 Redis 缓存，TTL 与 Token 剩余有效期对齐
    if user_obj:
        ttl = max(1, int((db_token.expires_at - datetime.now()).total_seconds()))
        await cache_user_token(token, user_obj.id, ttl)
        logger.info(f"✅ Token 查询成功并已缓存，user_id={user_obj.id}，TTL={ttl}s")

    return user_obj
