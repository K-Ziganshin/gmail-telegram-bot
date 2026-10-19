"""Inbox processing: classify unread mail and apply the matching action."""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .mail_filter import classify

log = logging.getLogger(__name__)
Kind = Literal["important", "unwanted", "ignored"]


class MailBox(Protocol):
    def unread_ids(self) -> list[str]: ...
    def get(self, msg_id: str) -> dict[str, Any]: ...
    def mark_read(self, msg_id: str) -> None: ...
    def trash(self, msg_id: str) -> None: ...
    def pause(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class Mail:
    kind: Kind
    sender: str = ""
    subject: str = ""
    snippet: str = ""


@dataclass
class Report:
    mails: list[Mail] = field(default_factory=list)

    @property
    def counts(self) -> Counter[str]:
        return Counter(m.kind for m in self.mails)

    @property
    def important(self) -> list[Mail]:
        return [m for m in self.mails if m.kind == "important"]


def header(message: dict[str, Any], name: str) -> str:
    """Case-insensitive lookup of a header value in a Gmail API message."""
    for h in message.get("payload", {}).get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def process_unread(box: MailBox, pause_between: float = 0.5) -> Report:
    """Important -> mark read and report; unwanted -> Trash; everything else stays unread."""
    report = Report()
    for msg_id in box.unread_ids():
        box.pause(pause_between)  # spread requests over time to stay well under the quota
        message = box.get(msg_id)
        mail = Mail(
            classify(header(message, "Subject"), message.get("snippet", "")),
            header(message, "From"),
            header(message, "Subject"),
            message.get("snippet", ""),
        )
        if mail.kind == "important":
            box.mark_read(msg_id)
        elif mail.kind == "unwanted":
            box.trash(msg_id)
        report.mails.append(mail)
    c = report.counts
    log.info("Inbox processed: %d unread, %d important, %d trashed", len(report.mails), c["important"], c["unwanted"])
    return report
