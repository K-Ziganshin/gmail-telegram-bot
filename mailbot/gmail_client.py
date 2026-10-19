"""Thin wrapper over the Gmail API with retries on quota errors.

All methods are synchronous; the bot calls them via ``asyncio.to_thread`` so the
event loop is never blocked.
"""

from __future__ import annotations

import base64
import logging
import time
from collections.abc import Callable
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, TypeVar

from googleapiclient.errors import HttpError

from .config import SCOPES

log = logging.getLogger(__name__)
T = TypeVar("T")
RETRY_STATUSES = frozenset({403, 429})


class GmailQuotaError(RuntimeError):
    """Gmail kept answering 403/429 after every retry."""


def with_backoff(request: Callable[[], T], max_retries: int = 5, sleep: Callable[[float], None] = time.sleep) -> T:
    """Run ``request``; on 403/429 wait 2, 3, 5, 9, 17 s and retry. Other errors are re-raised."""
    for attempt in range(max_retries):
        try:
            return request()
        except HttpError as error:
            if error.resp.status not in RETRY_STATUSES:
                raise
            delay = 2**attempt + 1
            log.warning(
                "Gmail quota hit (HTTP %s), retry %d/%d in %ds", error.resp.status, attempt + 1, max_retries, delay
            )
            sleep(delay)
    raise GmailQuotaError(f"Gmail API still rate-limited after {max_retries} retries")


def build_service(credentials_path: Path, token_path: Path) -> Any:
    """OAuth 2.0 desktop flow: reuse token.json, refresh it, or ask for consent in the browser once."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"{credentials_path.name} not found - download the OAuth client from Google Cloud Console"
                )
            creds = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES).run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class GmailClient:
    def __init__(self, service: Any, sleep: Callable[[float], None] = time.sleep) -> None:
        self._messages = service.users().messages()
        self._sleep = sleep

    def _run(self, request: Any) -> Any:
        return with_backoff(request.execute, sleep=self._sleep)

    def unread_ids(self) -> list[str]:
        result = self._run(self._messages.list(userId="me", q="is:unread"))
        return [m["id"] for m in result.get("messages", [])]

    def get(self, msg_id: str) -> dict[str, Any]:
        return self._run(self._messages.get(userId="me", id=msg_id, format="full"))

    def mark_read(self, msg_id: str) -> None:
        self._run(self._messages.batchModify(userId="me", body={"removeLabelIds": ["UNREAD"], "ids": [msg_id]}))

    def trash(self, msg_id: str) -> None:
        """Move to Trash (recoverable for 30 days) - never a permanent delete."""
        self._run(self._messages.trash(userId="me", id=msg_id))

    def send(self, to: str, subject: str, body: str) -> None:
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self._run(self._messages.send(userId="me", body={"raw": raw}))

    def pause(self, seconds: float) -> None:
        self._sleep(seconds)
