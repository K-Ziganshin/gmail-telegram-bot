import pytest

from mailbot.config import ConfigError, Settings
from mailbot.processing import Mail
from mailbot.texts import important_mail, looks_like_email


def test_settings_from_env():
    s = Settings.from_env({"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "123", "CHECK_INTERVAL": "30"})
    assert (s.owner_chat_id, s.check_interval) == (123, 30)


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "abc"},
        {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1", "CHECK_INTERVAL": "5"},
    ],
)
def test_settings_validation(env):
    with pytest.raises(ConfigError):
        Settings.from_env(env)


@pytest.mark.parametrize(
    ("value", "ok"), [("a@b.co", True), ("no-at.com", False), ("a@b", False), ("a b@c.d", False), ("a@.com", False)]
)
def test_looks_like_email(value, ok):
    assert looks_like_email(value) is ok


def test_important_mail_is_html_escaped():
    text = important_mail(Mail("important", "<script>", "a & b", "x"))
    assert "<script>" not in text and "&lt;script&gt;" in text and "a &amp; b" in text


def test_router_builds_with_owner_filter():
    from unittest.mock import MagicMock
    from zoneinfo import ZoneInfo

    from mailbot.handlers import Monitor, build_router

    router = build_router(Monitor(gmail=MagicMock(), owner_chat_id=1, interval=60, tz=ZoneInfo("UTC")))
    assert router.message.handlers and router.callback_query.handlers
