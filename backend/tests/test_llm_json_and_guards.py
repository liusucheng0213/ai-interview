"""不连数据库、不调用模型，只检查这次修过的纯逻辑。"""
import sys
from pathlib import Path

from fastapi import HTTPException

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from routers.interview import _assert_same_interview  # noqa: E402
from services.LLM_services import _parse_llm_json_dict  # noqa: E402


class _History:
    def __init__(self, interview_id: int):
        self.id = interview_id


def test_fenced_json_and_preamble():
    fenced, err = _parse_llm_json_dict('```json\n{"score": 1}\n```')
    assert err is None
    assert fenced["score"] == 1

    preamble, err = _parse_llm_json_dict('说明如下：\n{"score": 2, "note": "json"}')
    assert err is None
    assert preamble["score"] == 2
    assert preamble["note"] == "json"


def test_charset_strip_does_not_eat_json_text():
    """旧实现用 lstrip('```json')，会把开头的 j/s/o/n 当垃圾删掉。"""
    data, err = _parse_llm_json_dict('{"json_ok": true, "name": "note"}')
    assert err is None
    assert data["json_ok"] is True
    assert data["name"] == "note"


def test_interview_id_guard():
    history = _History(7)
    _assert_same_interview(None, history)
    _assert_same_interview("null", history)
    _assert_same_interview("7", history)
    try:
        _assert_same_interview("8", history)
        raise AssertionError("mismatched interview id should fail")
    except HTTPException as exc:
        assert exc.status_code == 400
    try:
        _assert_same_interview("abc", history)
        raise AssertionError("invalid interview id should fail")
    except HTTPException as exc:
        assert exc.status_code == 400
