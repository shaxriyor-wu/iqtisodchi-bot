from types import SimpleNamespace

from app.bot.middlewares.access import AccessMiddleware
from app.config import Settings


def _u(id, username):
    return SimpleNamespace(id=id, username=username)


def test_username_match_is_case_insensitive():
    a = AccessMiddleware(["shakh_wu", "smdv_19"], [])
    assert a._allowed(_u(1, "Shakh_WU"))
    assert a._allowed(_u(2, "smdv_19"))
    assert not a._allowed(_u(3, "someone_else"))
    assert not a._allowed(_u(4, None))


def test_id_allows_even_without_username():
    a = AccessMiddleware([], [42])
    assert a._allowed(_u(42, None))
    assert not a._allowed(_u(43, "x"))


def test_empty_lists_deny_everyone():
    assert not AccessMiddleware([], [])._allowed(_u(1, "shakh_wu"))


def test_settings_parse_env_strings(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "x")
    monkeypatch.setenv("ALLOWED_USERNAMES", "@Shakh_wu, smdv_19 ,")
    monkeypatch.setenv("ALLOWED_USER_IDS", "")
    s = Settings(_env_file=None)
    assert s.allowed_usernames == ["shakh_wu", "smdv_19"]
    assert s.allowed_user_ids == []
