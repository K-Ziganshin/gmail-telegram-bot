"""Telegram message texts and inline keyboards."""

from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .processing import Mail, Report


def main_keyboard(monitoring: bool) -> InlineKeyboardMarkup:
    toggle = "⏸ Приостановить автопроверку" if monitoring else "▶️ Возобновить автопроверку"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Проверить сейчас", callback_data="check_mail"),
                InlineKeyboardButton(text="📊 Статус", callback_data="status_info"),
            ],
            [InlineKeyboardButton(text=toggle, callback_data="toggle_monitoring")],
            [InlineKeyboardButton(text="✉️ Написать письмо", callback_data="send_email_start")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 Отправить", callback_data="confirm_send"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send"),
            ]
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send")]])


def important_mail(mail: Mail) -> str:
    return (
        f"🚨 <b>Важное письмо в Gmail</b>\n\n<b>От:</b> {escape(mail.sender)}\n"
        f"<b>Тема:</b> {escape(mail.subject)}\n\n<b>Кратко:</b> {escape(mail.snippet)}"
    )


def manual_check(report: Report) -> str:
    c = report.counts
    return (
        f"✅ <b>Проверка завершена</b>\n\n• Непрочитанных: <b>{len(report.mails)}</b>\n"
        f"• Важных: <b>{c['important']}</b>\n• Перемещено в корзину: <b>{c['unwanted']}</b>"
    )


def email_preview(to: str, subject: str, body: str) -> str:
    return (
        f"📋 <b>Проверьте письмо перед отправкой:</b>\n\n<b>Кому:</b> <code>{escape(to)}</code>\n"
        f"<b>Тема:</b> {escape(subject)}\n<b>Текст:</b>\n{escape(body)}"
    )


def looks_like_email(value: str) -> bool:
    local, _, domain = value.partition("@")
    return (
        bool(local) and "." in domain and " " not in value and not domain.startswith(".") and not domain.endswith(".")
    )
