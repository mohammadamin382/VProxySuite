from __future__ import annotations

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def kb_start() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ ثبت کانفیگ", callback_data="cfg:new")
    kb.button(text="ℹ️ راهنما", callback_data="help:open")
    kb.adjust(2)
    return kb
