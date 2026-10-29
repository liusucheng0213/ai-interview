import importlib
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from config.env_util import env_int, env_raw, env_str  # noqa: E402


def test_env_str_uses_default_for_unset_and_blank_values(monkeypatch):
    monkeypatch.delenv("CONFIG_TEST_VALUE", raising=False)
    assert env_str("CONFIG_TEST_VALUE", "fallback") == "fallback"

    monkeypatch.setenv("CONFIG_TEST_VALUE", "  \t")
    assert env_str("CONFIG_TEST_VALUE", "fallback") == "fallback"

    monkeypatch.setenv("CONFIG_TEST_VALUE", "  configured  ")
    assert env_str("CONFIG_TEST_VALUE", "fallback") == "configured"


def test_env_raw_preserves_an_explicit_blank_value(monkeypatch):
    monkeypatch.delenv("CONFIG_TEST_VALUE", raising=False)
    assert env_raw("CONFIG_TEST_VALUE", "fallback") == "fallback"

    monkeypatch.setenv("CONFIG_TEST_VALUE", "")
    assert env_raw("CONFIG_TEST_VALUE", "fallback") == ""

    monkeypatch.setenv("CONFIG_TEST_VALUE", "  configured  ")
    assert env_raw("CONFIG_TEST_VALUE", "fallback") == "configured"


def test_env_int_uses_default_only_for_unset_or_blank_values(monkeypatch):
    monkeypatch.delenv("CONFIG_TEST_INT", raising=False)
    assert env_int("CONFIG_TEST_INT", 20) == 20

    monkeypatch.setenv("CONFIG_TEST_INT", "  ")
    assert env_int("CONFIG_TEST_INT", 20) == 20

    monkeypatch.setenv("CONFIG_TEST_INT", " 7 ")
    assert env_int("CONFIG_TEST_INT", 20) == 7

    monkeypatch.setenv("CONFIG_TEST_INT", "not-an-integer")
    with pytest.raises(ValueError):
        env_int("CONFIG_TEST_INT", 20)


def test_mysql_url_preserves_special_character_credentials(monkeypatch):
    import config.db_conf as db_conf

    monkeypatch.setenv("MYSQL_USER", "release+user@example.com")
    monkeypatch.setenv("MYSQL_PASSWORD", "p@ss:word/?#[]%+")
    monkeypatch.setenv("MYSQL_HOST", "db.internal")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_DB", "interview_test")

    try:
        db_conf = importlib.reload(db_conf)
        url = db_conf.MYSQL_URL

        assert url.username == "release+user@example.com"
        assert url.password == "p@ss:word/?#[]%+"
        assert url.host == "db.internal"
        assert url.port == 3307
        assert url.database == "interview_test"
        assert db_conf.async_engine.url.database == "interview_test"
    finally:
        monkeypatch.undo()
        importlib.reload(db_conf)
