"""企业共享 knowledge_file：求职者检索排除偏好。"""
import json
import logging
from typing import Set

logger = logging.getLogger(__name__)


def parse_enterprise_kf_disabled(user) -> Set[int]:
    raw = getattr(user, "enterprise_kf_disabled_json", None) or "[]"
    if isinstance(raw, list):
        try:
            return {int(x) for x in raw}
        except (TypeError, ValueError):
            return set()
    try:
        data = json.loads(raw) if isinstance(raw, str) else []
        return {int(x) for x in data}
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.debug("[enterprise_kf] 解析失败：%s", e)
        return set()


def serialize_enterprise_kf_disabled(ids: Set[int]) -> str:
    return json.dumps(sorted(ids), ensure_ascii=False)
