"""Settings loaded from environment variables (.env) and validated at start-up."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
SCOPES = ("https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send")


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or malformed."""


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_chat_id: int
    check_interval: int = 60
    credentials_path: Path = BASE_DIR / "credentials.json"
    token_path: Path = BASE_DIR / "token.json"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        if env is None:
            load_dotenv(BASE_DIR / ".env")
            env = dict(os.environ)
        token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ConfigError("TELEGRAM_BOT_TOKEN is not set (see .env.example)")
        try:
            chat_id = int(env.get("TELEGRAM_CHAT_ID", ""))
        except ValueError as exc:
            raise ConfigError("TELEGRAM_CHAT_ID must be a numeric chat id") from exc
        try:
            interval = int(env.get("CHECK_INTERVAL", "60"))
        except ValueError as exc:
            raise ConfigError("CHECK_INTERVAL must be an integer number of seconds") from exc
        if interval < 15:
            raise ConfigError("CHECK_INTERVAL must be at least 15 seconds")
        return cls(bot_token=token, owner_chat_id=chat_id, check_interval=interval)
