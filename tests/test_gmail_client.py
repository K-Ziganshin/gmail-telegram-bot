from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from mailbot.gmail_client import GmailClient, GmailQuotaError, with_backoff


def http_error(status):
    return HttpError(SimpleNamespace(status=status, reason="x"), b"{}")


def test_backoff_retries_quota_errors_then_succeeds():
    calls, sleeps = iter([http_error(429), http_error(403), "ok"]), []

    def request():
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    assert with_backoff(request, sleep=sleeps.append) == "ok"
    assert sleeps == [2, 3]


def test_backoff_gives_up():
    def request():
        raise http_error(429)

    with pytest.raises(GmailQuotaError):
        with_backoff(request, max_retries=3, sleep=lambda s: None)


def test_backoff_does_not_retry_other_errors():
    def request():
        raise http_error(404)

    with pytest.raises(HttpError):
        with_backoff(request, sleep=lambda s: pytest.fail("should not sleep"))


def test_client_uses_trash_not_delete_and_encodes_mail():
    service = MagicMock()
    msgs = service.users.return_value.messages.return_value
    client = GmailClient(service, sleep=lambda s: None)

    client.trash("42")
    msgs.trash.assert_called_once_with(userId="me", id="42")
    msgs.delete.assert_not_called()

    client.send("a@example.com", "Тема", "Текст")
    raw = msgs.send.call_args.kwargs["body"]["raw"]
    assert isinstance(raw, str) and raw


def test_unread_ids():
    service = MagicMock()
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": [{"id": "1"}, {"id": "2"}]
    }
    assert GmailClient(service).unread_ids() == ["1", "2"]
