import logging

import bcrypt

logger = logging.getLogger(__name__)


def get_hash_password(password: str) -> str:
    try:
        password_bytes = password.encode("utf-8")[:70]
        # rounds=10：在安全性与性能间取较优平衡（rounds=12 约 400ms，rounds=10 约 100ms）
        salt = bcrypt.gensalt(rounds=10)
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
