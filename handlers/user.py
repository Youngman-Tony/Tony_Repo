from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import database as db
from keyboards import get_bid_keyboard, get_participate_keyboard


async def cb_participate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])

    auction = await db.get_auction(auction_id)
    if not auction or auction["status"] != "active":
        await query.answer("Этот розыгрыш уже не активен.", show_alert=True)
        return

    end_dt = datetime.fromisoformat(auction["end_time"])
    if datetime.now() >= end_dt:
        await query.answer("Розыгрыш уже завершён.", show_alert=True)
        return

    user = query.from_user
    current_user_bid = await db.get_user_bid(auction_id, user.id)

    if current_user_bid:
        current_amount = current_user_bid["amount"]
    else:
        current_amount = auction["min_bid"]

    step = auction["step"]

    if current_amount == auction["min_bid"] and not current_user_bid:
        text = (
            f"🎯 <b>{auction['title']}</b>\n\n"
            f"💰 Минимальная ставка: <b>{auction['min_bid']} руб.</b>\n"
            f"📈 Шаг: <b>{step} руб.</b>\n\n"
            f"Нажмите «+{step} руб.» чтобы сделать первую ставку!"
        )
    else:
        top_bid = await db.get_top_bid(auction_id)
        leader_text = ""
        if top_bid and top_bid["user_id"] != user.id:
            leader_text = f"👑 Текущий лидер: @{top_bid['username'] or 'неизвестный'} — <b>{top_bid['amount']} руб.</b>\n\n"

        text = (
            f"🎯 <b>{auction['title']}</b>\n\n"
            f"📊 Ваша текущая ставка: <b>{current_amount} руб.</b>\n\n"
            f"{leader_text}"
            f"Нажмите «+{step} руб.» чтобы увеличить ставку, "
            f"затем «Принять ставку» для подтверждения."
        )

    context.user_data["current_amount"] = current_amount
    context.user_data["auction_id"] = auction_id

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_bid_keyboard(auction_id, current_amount, step),
    )


async def cb_increase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])

    auction = await db.get_auction(auction_id)
    if not auction or auction["status"] != "active":
        await query.answer("Розыгрыш не активен.", show_alert=True)
        return

    user = query.from_user
    current_amount = context.user_data.get("current_amount", auction["min_bid"])
    new_amount = current_amount + auction["step"]

    context.user_data["current_amount"] = new_amount

    top_bid = await db.get_top_bid(auction_id)
    leader_text = ""
    if top_bid and top_bid["user_id"] != user.id:
        leader_text = f"👑 Текущий лидер: @{top_bid['username'] or 'неизвестный'} — <b>{top_bid['amount']} руб.</b>\n\n"

    text = (
        f"🎯 <b>{auction['title']}</b>\n\n"
        f"📊 Ваша текущая ставка: <b>{new_amount} руб.</b>\n\n"
        f"{leader_text}"
        f"Нажмите «+{auction['step']} руб.» чтобы увеличить, "
        f"или «Принять ставку» для подтверждения."
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_bid_keyboard(auction_id, new_amount, auction["step"]),
    )


async def cb_accept_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])

    auction = await db.get_auction(auction_id)
    if not auction or auction["status"] != "active":
        await query.edit_message_text("❌ Розыгрыш уже не активен.")
        return

    end_dt = datetime.fromisoformat(auction["end_time"])
    if datetime.now() >= end_dt:
        await query.edit_message_text("❌ Розыгрыш уже завершён.")
        return

    user = query.from_user
    amount = context.user_data.get("current_amount", auction["min_bid"])

    top_bid = await db.get_top_bid(auction_id)
    if top_bid and top_bid["amount"] == amount and top_bid["user_id"] != user.id:
        await query.answer(
            "⚠️ Сейчас такую же ставку сделал другой участник, подождите или увеличьте свою.",
            show_alert=True,
        )
        return

    await db.add_bid(auction_id, user.id, user.username, amount)

    await query.edit_message_text(
        f"✅ <b>Ваша ставка принята!</b>\n\n"
        f"Итоговая сумма: <b>{amount} руб.</b>\n\n"
        f"Ожидайте завершения розыгрыша. Удачи!",
        parse_mode=ParseMode.HTML,
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 Используйте кнопку «Участвовать» в канале для входа в розыгрыш."
    )


def get_user_callback_handlers():
    return [
        cb_participate,
        cb_increase,
        cb_accept_bid,
        back_to_menu,
    ]
