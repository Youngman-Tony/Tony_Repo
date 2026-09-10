from datetime import datetime

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)
from telegram.constants import ParseMode

import database as db
from config import ADMIN_IDS, CHANNEL_ID
from keyboards import (
    get_main_menu_keyboard,
    get_auction_preview_keyboard,
    get_admin_auctions_keyboard,
    get_admin_auction_detail_keyboard,
    get_bids_keyboard,
    get_participate_keyboard,
)

(
    TITLE, MIN_BID, STEP, START_DATE, START_TIME,
    END_DATE, END_TIME, PHOTO, PREVIEW
) = range(9)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Этот бот доступен только для администраторов.")
        return ConversationHandler.END
    await update.message.reply_text(
        "👋 Добро пожаловать в панель управления аукционами!\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


async def cb_create_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.edit_message_text("Нет доступа.")
        return ConversationHandler.END
    await query.edit_message_text("📝 Введите описание (название) розыгрыша:")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("💰 Введите минимальную ставку (в рублях):")
    return MIN_BID


async def get_min_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("Введите положительное число:")
        return MIN_BID
    context.user_data["min_bid"] = int(text)
    await update.message.reply_text("📈 Введите минимальный шаг увеличения ставки (в рублях):")
    return STEP


async def get_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("Введите положительное число:")
        return STEP
    context.user_data["step"] = int(text)
    await update.message.reply_text(
        "📅 Введите дату начала розыгрыша в формате ДД.ММ.ГГГГ:"
    )
    return START_DATE


async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ:")
        return START_DATE
    context.user_data["start_date"] = text
    await update.message.reply_text("⏰ Введите время начала в формате ЧЧ:ММ:")
    return START_TIME


async def get_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите время в формате ЧЧ:ММ:")
        return START_TIME
    context.user_data["start_time"] = text
    await update.message.reply_text(
        "📅 Введите дату завершения розыгрыша в формате ДД.ММ.ГГГГ:"
    )
    return END_DATE


async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату в формате ДД.ММ.ГГГГ:")
        return END_DATE
    context.user_data["end_date"] = text
    await update.message.reply_text("⏰ Введите время завершения в формате ЧЧ:ММ:")
    return END_TIME


async def get_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите время в формате ЧЧ:ММ:")
        return END_TIME
    context.user_data["end_time"] = text
    await update.message.reply_text("🖼 Отправьте изображение для розыгрыша (или отправьте /skip чтобы пропустить):")
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["photo_id"] = update.message.photo[-1].file_id
    else:
        context.user_data["photo_id"] = None

    start_dt = datetime.strptime(
        f"{context.user_data['start_date']} {context.user_data['start_time']}", "%d.%m.%Y %H:%M"
    )
    end_dt = datetime.strptime(
        f"{context.user_data['end_date']} {context.user_data['end_time']}", "%d.%m.%Y %H:%M"
    )

    if end_dt <= start_dt:
        await update.message.reply_text(
            "❌ Время завершения должно быть позже времени начала. Попробуйте снова.\n"
            "Введите дату начала в формате ДД.ММ.ГГГГ:"
        )
        return START_DATE

    context.user_data["start_dt"] = start_dt.isoformat()
    context.user_data["end_dt"] = end_dt.isoformat()

    auction_id = await db.create_auction(
        admin_id=update.effective_user.id,
        title=context.user_data["title"],
        min_bid=context.user_data["min_bid"],
        step=context.user_data["step"],
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        photo_id=context.user_data["photo_id"],
    )
    context.user_data["auction_id"] = auction_id

    await _send_preview(update, context, auction_id)
    return PREVIEW


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_id"] = None

    start_dt = datetime.strptime(
        f"{context.user_data['start_date']} {context.user_data['start_time']}", "%d.%m.%Y %H:%M"
    )
    end_dt = datetime.strptime(
        f"{context.user_data['end_date']} {context.user_data['end_time']}", "%d.%m.%Y %H:%M"
    )

    if end_dt <= start_dt:
        await update.message.reply_text(
            "❌ Время завершения должно быть позже времени начала.\n"
            "Введите дату начала в формате ДД.ММ.ГГГГ:"
        )
        return START_DATE

    context.user_data["start_dt"] = start_dt.isoformat()
    context.user_data["end_dt"] = end_dt.isoformat()

    auction_id = await db.create_auction(
        admin_id=update.effective_user.id,
        title=context.user_data["title"],
        min_bid=context.user_data["min_bid"],
        step=context.user_data["step"],
        start_time=start_dt.isoformat(),
        end_time=end_dt.isoformat(),
        photo_id=None,
    )
    context.user_data["auction_id"] = auction_id

    await _send_preview(update, context, auction_id)
    return PREVIEW


async def _send_preview(update_or_query, context, auction_id):
    auction = await db.get_auction(auction_id)
    text = _build_auction_text(auction)

    send_method = update_or_query.message
    if update_or_query.callback_query:
        send_method = update_or_query.callback_query.message

    if auction["photo_id"]:
        await send_method.reply_photo(
            photo=auction["photo_id"],
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_auction_preview_keyboard(auction_id),
        )
    else:
        await send_method.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_auction_preview_keyboard(auction_id),
        )


def _build_auction_text(auction):
    start = datetime.fromisoformat(auction["start_time"]).strftime("%d.%m.%Y %H:%M")
    end = datetime.fromisoformat(auction["end_time"]).strftime("%d.%m.%Y %H:%M")
    return (
        f"🎯 <b>{auction['title']}</b>\n\n"
        f"💰 Минимальная ставка: <b>{auction['min_bid']} руб.</b>\n"
        f"📈 Шаг увеличения: <b>{auction['step']} руб.</b>\n\n"
        f"📅 Начало: <b>{start}</b>\n"
        f"📅 Завершение: <b>{end}</b>\n\n"
        f"Статус: {'📝 Черновик' if auction['status'] == 'draft' else '🟢 Активен' if auction['status'] == 'active' else '🔴 Завершён'}"
    )


async def cb_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)
    text = _build_auction_text(auction)

    if auction["photo_id"]:
        await query.message.edit_media(
            InputMediaPhoto(media=auction["photo_id"], caption=text, parse_mode=ParseMode.HTML),
            reply_markup=get_auction_preview_keyboard(auction_id),
        )
    else:
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_auction_preview_keyboard(auction_id),
        )


async def cb_start_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)

    if auction["status"] != "draft":
        await query.edit_message_text("❌ Этот розыгрыш уже запущен или завершён.")
        return

    start_dt = datetime.fromisoformat(auction["start_time"])
    end_dt = datetime.fromisoformat(auction["end_time"])
    now = datetime.now()

    if start_dt > now:
        await query.edit_message_text(
            f"⏰ Розыгрыш запланирован на {start_dt.strftime('%d.%m.%Y %H:%M')}. "
            f"Бот автоматически опубликует его в канале в указанное время."
        )
        await db.update_auction_status(auction_id, "scheduled")
        return

    await db.update_auction_status(auction_id, "active")

    channel_text = (
        f"🎯 <b>РОЗЫГРЫШ ЗАПУЩЕН!</b>\n\n"
        f"🎁 <b>{auction['title']}</b>\n\n"
        f"💰 Минимальная ставка: <b>{auction['min_bid']} руб.</b>\n"
        f"📈 Шаг: <b>{auction['step']} руб.</b>\n\n"
        f"⏰ Завершение: <b>{end_dt.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"Нажмите «Участвовать», чтобы сделать ставку!"
    )

    if auction["photo_id"]:
        msg = await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=auction["photo_id"],
            caption=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_participate_keyboard(auction_id),
        )
    else:
        msg = await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_participate_keyboard(auction_id),
        )

    await db.update_auction_status(auction_id, "active", channel_message_id=msg.message_id)

    await query.edit_message_text("✅ Розыгрыш запущен и опубликован в канале!")

    from scheduler import schedule_auction_end
    schedule_auction_end(context.job_queue, auction_id, end_dt, context)


async def cb_cancel_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    await db.update_auction_status(auction_id, "cancelled")
    await query.edit_message_text("❌ Розыгрыш отменён.")


async def cb_my_auctions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auctions = await db.get_all_auctions_by_admin(query.from_user.id)
    if not auctions:
        await query.edit_message_text("📋 У вас пока нет розыгрышей.\n\nНажмите «Создать розыгрыш» чтобы начать.")
        return
    await query.edit_message_text(
        "📋 Ваши розыгрыши:",
        reply_markup=get_admin_auctions_keyboard(auctions)
    )


async def cb_admin_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)
    text = _build_auction_text(auction)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_auction_detail_keyboard(auction_id, auction["status"]),
    )


async def cb_view_bids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    bids = await db.get_bids_for_auction(auction_id)
    if not bids:
        await query.edit_message_text("📊 Ставок пока нет.")
        return
    text = "📊 <b>Ставки (по убыванию):</b>\n\n"
    for i, bid in enumerate(bids, 1):
        text += f"{i}. @{bid['username'] or 'нет_юзера'} — <b>{bid['amount']} руб.</b>\n"
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_bids_keyboard(bids, auction_id),
    )


async def cb_select_winner_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    auction_id = int(parts[1])
    bid_id = int(parts[2])

    bids = await db.get_bids_for_auction(auction_id)
    winning_bid = None
    for b in bids:
        if b["id"] == bid_id:
            winning_bid = b
            break

    if not winning_bid:
        await query.edit_message_text("❌ Ставка не найдена.")
        return

    await db.set_winner(auction_id, winning_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    auction = await db.get_auction(auction_id)

    winner_text = (
        f"🏆 <b>ПОБЕДИТЕЛЬ РОЗЫГРЫША!</b>\n\n"
        f"🎁 {auction['title']}\n\n"
        f"Победитель: @{winning_bid['username'] or winning_bid['user_id']}\n"
        f"Ставка: <b>{winning_bid['amount']} руб.</b>\n\n"
        f"Для получения приза обратитесь к администратору канала."
    )

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    await query.edit_message_text(f"✅ Победитель назначен: @{winning_bid['username'] or winning_bid['user_id']}")


async def cb_finish_early(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])

    top_bid = await db.get_top_bid(auction_id)
    auction = await db.get_auction(auction_id)

    if not top_bid:
        await db.update_auction_status(auction_id, "finished")
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🔴 Розыгрыш «{auction['title']}» завершён досрочно.\n"
                 f"Ставок не было, победитель не определён.",
            parse_mode=ParseMode.HTML,
        )
        await query.edit_message_text("✅ Розыгрыш завершён (без ставок).")
        return

    await db.set_winner(auction_id, top_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    winner_text = (
        f"🏆 <b>ПОБЕДИТЕЛЬ РОЗЫГРЫША!</b>\n\n"
        f"🎁 {auction['title']}\n\n"
        f"Победитель: @{top_bid['username'] or top_bid['user_id']}\n"
        f"Ставка: <b>{top_bid['amount']} руб.</b>\n\n"
        f"Для получения приза обратитесь к администратору канала."
    )

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    await query.edit_message_text(
        f"✅ Розыгрыш завершён досрочно. Победитель: @{top_bid['username'] or top_bid['user_id']}"
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 Панель управления аукционами:",
        reply_markup=get_main_menu_keyboard()
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Создание розыгрыша отменено.")
    return ConversationHandler.END


def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_create_auction, pattern="^create_auction$"),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            MIN_BID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_min_bid)],
            STEP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_step)],
            START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_date)],
            START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_time)],
            END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_date)],
            END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_time)],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.Regex("^/skip$"), skip_photo),
            ],
            PREVIEW: [
                CallbackQueryHandler(cb_preview, pattern="^preview:"),
                CallbackQueryHandler(cb_start_auction, pattern="^start_auction:"),
                CallbackQueryHandler(cb_cancel_auction, pattern="^cancel_auction:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
