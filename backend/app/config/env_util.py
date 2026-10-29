"""读取环境变量。

env_str / env_int 把空白视为未设置，并回退到默认值。
这样把 backend/.env.example 复制成 .env 后，未填写的可选项不会覆盖代码默认值。
env_raw 保留显式空值，只在键完全不存在时使用默认值。
"""
from __future__ import annotations

import os


def env_raw(name: str, default: str = "") -> str:
    """键不存在时返回 default。键存在但为空时保留空字符串。"""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip()


def env_str(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    text = raw.strip()
    return text if text else default


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return int(raw.strip())
