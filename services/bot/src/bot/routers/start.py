    from __future__ import annotations

    import html

    from aiogram import Router, F
    from aiogram.filters import CommandStart, Command
    from aiogram.types import Message, CallbackQuery

    from bot.keyboards import kb_start
    from clients.api_client import APIClient

    router = Router(name="start")


    @router.message(CommandStart())
    async def on_start(m: Message) -> None:
        name = m.from_user.full_name if m.from_user else "کاربر عزیز"
        text = (
            f"سلام {html.escape(name)} 👋\n"
            f"به <b>VProxySuite</b> خوش اومدی!\n"
            f"با این ربات می‌تونی کانفیگ‌های <code>VLESS/VMESS</code> رو ارسال کنی و "
            f"تست‌های کارایی/پایداری/سازگاری و امنیت (با مجوز) بگیری."
        )
        await m.answer(text, reply_markup=kb_start().as_markup())


    @router.message(Command("ping"))
    async def on_ping(m: Message) -> None:
        client = APIClient()
        try:
            h = await client.health()
            await m.answer(f"✅ API OK: <code>{html.escape(str(h))}</code>")
        except Exception as e:  # noqa: BLE001
            await m.answer(f"❌ API Error: <code>{html.escape(str(e))}</code>")
        finally:
            await client.close()


    @router.callback_query(F.data == "help:open")
    async def on_help(cb: CallbackQuery) -> None:
        msg = (
            "راهنما:"
            "1) دکمه «ثبت کانفیگ» را بزن و رشته‌ی VLESS/VMESS را بفرست."
            "2) نوع تست‌ها را انتخاب کن. تست‌های پیشرفته‌ی امنیتی فقط با رضایت صریح اجرا می‌شود."
            "3) بعد از اتمام، خلاصه و گزارش کامل (HTML/PDF) دریافت می‌کنی."
        )
        await cb.message.answer(msg)
        await cb.answer()
