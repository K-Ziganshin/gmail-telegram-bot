import asyncio
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

from googleapiclient.errors import HttpError

from mailbot.handlers import Monitor, check_inbox
from tests.test_processing import FakeBox, gmail_message


def monitor(box):
    return Monitor(gmail=box, owner_chat_id=7, interval=60, tz=ZoneInfo("UTC"))


def test_check_inbox_notifies_owner_about_important_mail_only():
    bot = AsyncMock()
    box = FakeBox({"a": gmail_message("Ваш заказ оплачен"), "b": gmail_message("Акция недели")})
    report = asyncio.run(check_inbox(bot, monitor(box)))
    assert report.counts["important"] == 1
    bot.send_message.assert_awaited_once()
    assert bot.send_message.await_args.args[0] == 7


def test_check_inbox_survives_gmail_errors():
    class BrokenBox(FakeBox):
        def unread_ids(self):
            raise HttpError(type("R", (), {"status": 500, "reason": "x"})(), b"{}")

    bot = AsyncMock()
    assert asyncio.run(check_inbox(bot, monitor(BrokenBox({})))) is None
    bot.send_message.assert_not_awaited()
