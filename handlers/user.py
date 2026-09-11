from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import MSK
import database as db
from keyboards import get_bid_keyboard

BID_COOLDOWN = timedelta(minutes=5)


def _cooldown_remaining(auction_id, user_id, last_bid):
    if not last_bid:
        return None
    last_dt = datetime.fromisoformat(last_bid["created_at"])
    wait_until = last_dt + BID_COOLDOWN
    now = datetime.now(MSK)
    if now >= wait_until:
        return None
    return int((wait_until - now).total_seconds())


async def show_bid_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE, auction_id: int):
    auction = await db.get_auction(auction_id)
    if not auction:
        await update.message.reply_text("⚠️ Аукцион не найден. Возможно, он был удалён.")
        return
    if auction["status"] != "active":
        await update.message.reply_text("⛔️ Этот аукцион уже не активен.")
        return

    end_dt = datetime.fromisoformat(auction["end_time"])
    if datetime.now(MSK) >= end_dt:
        await update.message.reply_text("⛔️ Аукцион уже завершён.")
        return

    user = update.effective_user
    current_user_bid = await db.get_user_bid(auction_id, user.id)

    if current_user_bid:
        current_amount = current_user_bid["amount"]
    else:
        current_amount = auction["min_bid"]

    step = auction["step"]
    top_bid = await db.get_top_bid(auction_id)

    context.user_data["current_amount"] = current_amount
    context.user_data["auction_id"] = auction_id

    leader_text = ""
    if top_bid:
        if top_bid["user_id"] == user.id:
            leader_text = f"🏆 Вы сейчас лидер! Ставка: <b>{top_bid['amount']} руб.</b>\n\n"
        else:
            leader_text = f"👑 Текущий лидер: @{top_bid['username'] or 'неизвестный'} — <b>{top_bid['amount']} руб.</b>\n\n"

    text = (
        f"🎯 <b>{auction['title']}</b>\n\n"
        f"💰 Первоначальная цена: <b>{auction['min_bid']} руб.</b>\n"
        f"📈 Минимальная ставка: <b>{step} руб.</b>\n\n"
        f"{leader_text}"
        f"📊 Ваша ставка: <b>{current_amount} руб.</b>\n\n"
        f"Нажмите «+{step} руб.» чтобы увеличить ставку, "
        f"затем «Принять ставку» для подтверждения."
    )

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_bid_keyboard(auction_id, current_amount, step),
    )


async def cb_participate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    await show_bid_dialog(update, context, auction_id)


async def cb_increase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])

    auction = await db.get_auction(auction_id)
    if not auction:
        await query.answer("Аукцион не найден.", show_alert=True)
        return
    if auction["status"] != "active":
        await query.answer("Аукцион не активен.", show_alert=True)
        return

    user = query.from_user
    current = context.user_data.get("current_amount", auction["min_bid"])
    top_bid = await db.get_top_bid(auction_id)
    base_amount = max(current, top_bid["amount"] if top_bid else auction["min_bid"])
    new_amount = base_amount + auction["step"]

    context.user_data["current_amount"] = new_amount

    leader_text = ""
    if top_bid and top_bid["user_id"] != user.id:
        leader_text = f"👑 Текущий лидер: @{top_bid['username'] or 'неизвестный'} — <b>{top_bid['amount']} руб.</b>\n\n"
    elif top_bid:
        leader_text = f"🏆 Вы сейчас лидер! Ставка: <b>{top_bid['amount']} руб.</b>\n\n"

    text = (
        f"🎯 <b>{auction['title']}</b>\n\n"
        f"{leader_text}"
        f"📊 Ваша ставка: <b>{new_amount} руб.</b>\n\n"
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
    if not auction:
        await query.edit_message_text("❌ Аукцион не найден.")
        return
    if auction["status"] != "active":
        await query.edit_message_text("❌ Аукцион уже не активен.")
        return

    end_dt = datetime.fromisoformat(auction["end_time"])
    if datetime.now(MSK) >= end_dt:
        await query.edit_message_text("❌ Аукцион уже завершён.")
        return

    user = query.from_user
    amount = context.user_data.get("current_amount", auction["min_bid"])

    last_bid = await db.get_user_bid(auction_id, user.id)
    remaining = _cooldown_remaining(auction_id, user.id, last_bid)
    if remaining:
        minutes = (remaining + 59) // 60
        await query.answer(
            f"⏳ Повторить ставку можно не раньше, чем через {minutes} мин.",
            show_alert=True,
        )
        return

    top_bid = await db.get_top_bid(auction_id)
    if top_bid and top_bid["amount"] == amount and top_bid["user_id"] != user.id:
        await query.answer(
            "⚠️ Сейчас такую же ставку сделал другой участник, подождите или увеличьте свою.",
            show_alert=True,
        )
        return

    await db.add_bid(auction_id, user.id, user.username, amount)

    await query.edit_message_text(
        f"✅ <b>Ваша ставка принята!</b>\n"
        f"Итоговая сумма: <b>{amount} руб.</b>\n"
        f"Вы сможете сделать следующую ставку через 5 минут\n\n"
        f"Ожидайте завершения аукциона. Удачи!",
        parse_mode=ParseMode.HTML,
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 Используйте кнопку «Участвовать» в канале для входа в аукцион."
    )


def get_user_callback_handlers():
    return [
        cb_participate,
        cb_increase,
        cb_accept_bid,
        back_to_menu,
    ]