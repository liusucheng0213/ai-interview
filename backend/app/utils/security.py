import logging

import bcrypt

logger = logging.getLogger(__name__)

# rounds=12 约 400ms，rounds=10 约 100ms，取性能与安全的折中
BCRYPT_ROUNDS = 10


def get_hash_password(password: str) -> str:
    try:
        password_bytes = password.encode("utf-8")[:70]
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed_bytes = bcrypt.hashpw(password_bytes, salt)
        return hashed_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"密码加密失败：{e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")[:70]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"密码验证失败：{e}")
        return False
