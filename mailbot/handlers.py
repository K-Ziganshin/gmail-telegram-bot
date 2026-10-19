"""Telegram handlers: control panel, manual check, status and the compose-and-send dialog."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from googleapiclient.errors import HttpError

from . import texts
from .gmail_client import GmailClient, GmailQuotaError
from .mail_filter import IMPORTANT_KEYWORDS, UNWANTED_KEYWORDS
from .processing import Report, process_unread

log = logging.getLogger(__name__)
GMAIL_ERRORS = (HttpError, GmailQuotaError, OSError)


class SendEmail(StatesGroup):
    to = State()
    subject = State()
    body = State()
    confirm = State()


@dataclass
class Monitor:
    """Shared runtime state (replaces module-level globals)."""

    gmail: GmailClient
    owner_chat_id: int
    interval: int
    tz: ZoneInfo
    active: bool = True


async def check_inbox(bot: Bot, mon: Monitor) -> Report | None:
    try:
        report = await asyncio.to_thread(process_unread, mon.gmail)
    except GMAIL_ERRORS:
        log.exception("Inbox check failed")
        return None
    for mail in report.important:
        await bot.send_message(
            mon.owner_chat_id,
            texts.important_mail(mail),
            parse_mode="HTML",
            reply_markup=texts.main_keyboard(mon.active),
        )
    return report


async def auto_check_loop(bot: Bot, mon: Monitor) -> None:
    while True:
        if mon.active:
            await check_inbox(bot, mon)
        await asyncio.sleep(mon.interval)


def build_router(mon: Monitor) -> Router:
    router = Router()
    # only the owner's chat may control the bot - everything else is silently ignored
    router.message.filter(F.chat.id == mon.owner_chat_id)
    router.callback_query.filter(F.message.chat.id == mon.owner_chat_id)
    kb = lambda: texts.main_keyboard(mon.active)  # noqa: E731

    @router.message(Command("start"))
    async def start(message: types.Message, state: FSMContext) -> None:
        await state.clear()
        status = "🟢 включена" if mon.active else "🔴 приостановлена"
        await message.answer(
            f"👋 <b>Gmail-бот</b>\n\nАвтопроверка: <b>{status}</b>, каждые {mon.interval} с.",
            parse_mode="HTML",
            reply_markup=kb(),
        )

    @router.callback_query(F.data == "toggle_monitoring")
    async def toggle(callback: types.CallbackQuery) -> None:
        mon.active = not mon.active
        log.info("Auto-check %s by owner", "resumed" if mon.active else "paused")
        await callback.answer("Автопроверка " + ("возобновлена" if mon.active else "приостановлена"))
        await callback.message.edit_reply_markup(reply_markup=kb())

    @router.callback_query(F.data == "check_mail")
    async def check_now(callback: types.CallbackQuery, bot: Bot) -> None:
        await callback.answer("Проверяю ящик…")
        report = await check_inbox(bot, mon)
        text = texts.manual_check(report) if report else "⚠️ Не удалось проверить почту, подробности в логе."
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb())

    @router.callback_query(F.data == "status_info")
    async def status(callback: types.CallbackQuery) -> None:
        await callback.answer()
        try:
            unread = len(await asyncio.to_thread(mon.gmail.unread_ids))
        except GMAIL_ERRORS:
            log.exception("Status: unread count failed")
            unread = "н/д"
        now = datetime.now(mon.tz).strftime("%H:%M:%S %Z")
        await callback.message.answer(
            f"📊 <b>Состояние</b>\n\nАвтопроверка: {'🟢 активна' if mon.active else '⏸ пауза'}\n"
            f"Время: {now}\nНепрочитанных: {unread}\n\n"
            f"Важные слова: {', '.join(IMPORTANT_KEYWORDS[:5])}…\nВ корзину: {', '.join(UNWANTED_KEYWORDS[:5])}…",
            parse_mode="HTML",
            reply_markup=kb(),
        )

    @router.callback_query(F.data == "send_email_start")
    async def compose(callback: types.CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await state.set_state(SendEmail.to)
        await callback.message.answer("✉️ Введите адрес получателя:", reply_markup=texts.cancel_keyboard())

    @router.callback_query(F.data == "cancel_send")
    async def cancel(callback: types.CallbackQuery, state: FSMContext) -> None:
        await callback.answer("Отменено")
        await state.clear()
        await callback.message.answer("❌ Отправка отменена.", reply_markup=kb())

    @router.message(SendEmail.to)
    async def got_to(message: types.Message, state: FSMContext) -> None:
        to = (message.text or "").strip()
        if not texts.looks_like_email(to):
            await message.answer("⚠️ Это не похоже на e-mail. Ещё раз:", reply_markup=texts.cancel_keyboard())
            return
        await state.update_data(to=to)
        await state.set_state(SendEmail.subject)
        await message.answer("📌 Тема письма:", reply_markup=texts.cancel_keyboard())

    @router.message(SendEmail.subject)
    async def got_subject(message: types.Message, state: FSMContext) -> None:
        await state.update_data(subject=(message.text or "").strip())
        await state.set_state(SendEmail.body)
        await message.answer("📝 Текст письма:", reply_markup=texts.cancel_keyboard())

    @router.message(SendEmail.body)
    async def got_body(message: types.Message, state: FSMContext) -> None:
        await state.update_data(body=(message.text or "").strip())
        await state.set_state(SendEmail.confirm)
        d = await state.get_data()
        await message.answer(
            texts.email_preview(d["to"], d["subject"], d["body"]),
            parse_mode="HTML",
            reply_markup=texts.confirm_keyboard(),
        )

    @router.callback_query(SendEmail.confirm, F.data == "confirm_send")
    async def send(callback: types.CallbackQuery, state: FSMContext) -> None:
        await callback.answer("Отправляю…")
        d = await state.get_data()
        await state.clear()
        try:
            await asyncio.to_thread(mon.gmail.send, d["to"], d["subject"], d["body"])
        except GMAIL_ERRORS:
            log.exception("Sending e-mail failed")
            await callback.message.answer("❌ Письмо не отправлено, подробности в логе.", reply_markup=kb())
            return
        log.info("E-mail sent from Telegram")  # recipient is not logged on purpose
        await callback.message.answer("🚀 Письмо отправлено.", reply_markup=kb())

    @router.errors()
    async def on_error(event: types.ErrorEvent) -> bool:
        if isinstance(event.exception, TelegramAPIError):
            log.warning("Telegram API error: %s", event.exception)
        else:
            log.exception("Unhandled error in handler", exc_info=event.exception)
        return True

    return router
