# Gmail → Telegram Bot

![CI](https://github.com/K-Ziganshin/gmail-telegram-bot/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Async Telegram bot that monitors a Gmail inbox, forwards important mail to chat, cleans up promo mail and lets the owner write and send e-mails right from Telegram.

<!-- TODO (author): project description, screenshots / demo GIF -->

## Features
- Checks unread mail every 60 s (pause/resume and manual check via inline buttons)
- Keyword classification: important → pushed to Telegram, promo → moved to Trash
- Compose-and-send dialog (finite-state machine) with a confirmation step
- Exponential backoff on Gmail quota errors (403/429)
- Owner-only access: updates from any other chat are ignored

## Stack
Python 3.11+, aiogram 3, Gmail API (OAuth 2.0), asyncio

## Setup
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # fill in your values
python bot.py
```
1. Create a bot with [@BotFather](https://t.me/BotFather) and put its token into `.env`.
2. In Google Cloud Console enable the Gmail API, create an OAuth client of type *Desktop app*, download it as `credentials.json` next to `bot.py`. The first run opens a browser for consent and creates `token.json`.

## Configuration
| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Numeric ID of the only chat allowed to control the bot |

## Security
Secrets live only in `.env`, `credentials.json` and `token.json`, all git-ignored. Unwanted mail goes to Trash (recoverable), not permanent deletion.

## Development
```bash
pip install pytest ruff
ruff check . && pytest
```

License: MIT
