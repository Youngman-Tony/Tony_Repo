from datetime import datetime

from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
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
from handlers.user import show_bid_dialog
from keyboards import (
    get_main_menu_keyboard,
    get_auction_preview_keyboard,
    get_admin_auctions_keyboard,
    get_admin_auction_detail_keyboard,
    get_bids_keyboard,
    get_participate_keyboard,
    get_channels_keyboard,
    get_channel_detail_keyboard,
    get_channel_select_keyboard,
)

TITLE, MIN_BID, STEP, START_DATE, START_TIME, END_DATE, END_TIME, PHOTO, CHANNEL_SELECT, PREVIEW = range(10)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    args = context.args
    if args and args[0].startswith("auction_"):
        try:
            auction_id = int(args[0].split("_")[1])
        except (IndexError, ValueError):
            auction_id = None
        if auction_id:
            await show_bid_dialog(update, context, auction_id)
            return ConversationHandler.END

    if not await db.is_admin(user.id):
        await db.register_admin(user.id, user.username, user.first_name)
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Вы зарегистрированы как организатор розыгрышей.\n\n"
            f"Чтобы начать, добавьте бота в свой канал как администратора, "
            f"затем подключите канал через меню «Мои каналы»."
        )
    await update.message.reply_text(
        "👋 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👋 Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )


# ---------- Каналы ----------

async def cb_my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = await db.get_channels_by_admin(query.from_user.id)
    if not channels:
        await query.edit_message_text(
            "📢 У вас пока нет подключённых каналов.\n\n"
            "Добавьте бота в канал как администратора, затем нажмите "
            "«➕ Добавить канал» и перешлите любое сообщение из канала.",
            reply_markup=get_channels_keyboard(channels)
        )
    else:
        await query.edit_message_text(
            "📢 Ваши каналы:",
            reply_markup=get_channels_keyboard(channels)
        )


async def cb_channel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    channel = await db.get_channel(query.from_user.id, channel_id)
    if not channel:
        await query.edit_message_text("❌ Канал не найден.")
        return
    await query.edit_message_text(
        f"📢 <b>{channel['title'] or channel['username'] or channel['channel_id']}</b>\n\n"
        f"Канал подключён. Теперь можно создавать розыгрыши.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_channel_detail_keyboard(channel_id),
    )


async def cb_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 Чтобы подключить канал:\n\n"
        "1. Добавьте бота администратором в свой канал\n"
        "2. Перешлите сюда ЛЮБОЕ сообщение из этого канала\n\n"
        "Бот определит канал автоматически.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Назад", callback_data="my_channels")]
        ]),
    )
    context.user_data["awaiting_channel"] = True


async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_channel"):
        return

    msg = update.message
    forwarded = msg.forward_from_chat

    if not forwarded or forwarded.type != "channel":
        await msg.reply_text(
            "❌ Перешлите сообщение именно из канала, а не из чата/переписки.\n"
            "Попробуйте ещё раз или нажмите /cancel."
        )
        return

    context.user_data["awaiting_channel"] = False

    try:
        bot_member = await context.bot.get_chat_member(forwarded.id, context.bot.id)
        is_admin = bot_member.status in ("administrator", "creator")
    except Exception:
        is_admin = False

    if not is_admin:
        await msg.reply_text(
            f"❌ Бот не является администратором канала <b>@{forwarded.username or forwarded.title}</b>.\n\n"
            f"1. Откройте канал\n"
            f"2. Управление → Администраторы → Добавить администратора → найдите бота\n"
            f"3. Выдайте ему права (хотя бы для постинга)\n"
            f"4. Затем перешлите сюда сообщение из канала снова",
            parse_mode=ParseMode.HTML,
        )
        return

    await db.add_channel(
        admin_id=msg.from_user.id,
        channel_id=forwarded.id,
        title=forwarded.title,
        username=forwarded.username,
    )

    await msg.reply_text(
        f"✅ Канал <b>{forwarded.title or ('@' + forwarded.username if forwarded.username else '')}</b> подключён!",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )


async def cb_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    await db.remove_channel(query.from_user.id, channel_id)
    channels = await db.get_channels_by_admin(query.from_user.id)
    text = "📢 Ваши каналы:" if channels else "📢 Каналов нет.\n\nНажмите «➕ Добавить канал» чтобы подключить."
    await query.edit_message_text(text, reply_markup=get_channels_keyboard(channels))


# ---------- Создание розыгрыша ----------

async def cb_create_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Введите описание (название) розыгрыша:")
    return TITLE


async def cb_create_auction_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    context.user_data["channel_id"] = channel_id
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
    await update.message.reply_text("📅 Введите дату начала розыгрыша в формате ДД.ММ.ГГГГ:")
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
    await update.message.reply_text("📅 Введите дату завершения розыгрыша в формате ДД.ММ.ГГГГ:")
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
    await update.message.reply_text("🖼 Отправьте изображение для розыгрыша (или /skip чтобы пропустить):")
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

    return await _prompt_channel(update.message.from_user.id, context)


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

    return await _prompt_channel(update.message.from_user.id, context)


async def _prompt_channel(user_id, context):
    channels = await db.get_channels_by_admin(user_id)
    if not channels:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Сначала подключите канал!\n\n"
                 "Меню «📢 Мои каналы» → «➕ Добавить канал» → перешлите "
                 "сообщение из канала, в котором хотите проводить розыгрыш.",
            reply_markup=get_main_menu_keyboard(),
        )
        return ConversationHandler.END

    if len(channels) == 1:
        context.user_data["channel_id"] = channels[0]["channel_id"]
        return await _create_auction_record(user_id, context)

    await context.bot.send_message(
        chat_id=user_id,
        text="📢 Выберите канал для розыгрыша:",
        reply_markup=get_channel_select_keyboard(channels),
    )
    return CHANNEL_SELECT


async def cb_select_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    context.user_data["channel_id"] = channel_id
    return await _create_auction_record(query.from_user.id, context, query_message=query.message)


async def cb_cancel_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Создание розыгрыша отменено.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END


async def _create_auction_record(user_id, context, query_message=None):
    auction_id = await db.create_auction(
        admin_id=user_id,
        title=context.user_data["title"],
        min_bid=context.user_data["min_bid"],
        step=context.user_data["step"],
        start_time=context.user_data["start_dt"],
        end_time=context.user_data["end_dt"],
        photo_id=context.user_data["photo_id"],
        channel_id=context.user_data["channel_id"],
    )
    context.user_data["auction_id"] = auction_id

    auction = await db.get_auction(auction_id)
    text = _build_auction_text(auction)

    if query_message:
        if auction["photo_id"]:
            await query_message.reply_photo(
                photo=auction["photo_id"], caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_auction_preview_keyboard(auction_id),
            )
        else:
            await query_message.reply_text(
                text, parse_mode=ParseMode.HTML,
                reply_markup=get_auction_preview_keyboard(auction_id),
            )
    else:
        await context.bot.send_message(
            chat_id=user_id, text=text, parse_mode=ParseMode.HTML,
            reply_markup=get_auction_preview_keyboard(auction_id),
        )
    return PREVIEW


async def _build_auction_text(auction):
    start = datetime.fromisoformat(auction["start_time"]).strftime("%d.%m.%Y %H:%M")
    end = datetime.fromisoformat(auction["end_time"]).strftime("%d.%m.%Y %H:%M")
    status_map = {"draft": "📝 Черновик", "scheduled": "⏰ Запланирован", "active": "🟢 Активен", "finished": "🔴 Завершён", "cancelled": "❌ Отменён"}
    return (
        f"🎯 <b>{auction['title']}</b>\n\n"
        f"💰 Минимальная ставка: <b>{auction['min_bid']} руб.</b>\n"
        f"📈 Шаг увеличения: <b>{auction['step']} руб.</b>\n\n"
        f"📅 Начало: <b>{start}</b>\n"
        f"📅 Завершение: <b>{end}</b>\n\n"
        f"Статус: {status_map.get(auction['status'], auction['status'])}"
    )


# ---------- Предпросмотр / запуск ----------

async def cb_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)
    if not auction:
        await query.edit_message_text("❌ Розыгрыш не найден.")
        return
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

    if not auction:
        await query.edit_message_text("❌ Розыгрыш не найден.")
        return

    if auction["status"] not in ("draft", "scheduled"):
        await query.edit_message_text("❌ Этот розыгрыш уже запущен или завершён.")
        return

    channel_id = auction["channel_id"]
    start_dt = datetime.fromisoformat(auction["start_time"])
    end_dt = datetime.fromisoformat(auction["end_time"])
    now = datetime.now()

    if start_dt > now:
        await db.update_auction_status(auction_id, "scheduled")
        await query.edit_message_text(
            f"⏰ Розыгрыш запланирован на {start_dt.strftime('%d.%m.%Y %H:%M')}. "
            f"Бот автоматически опубликует его в канале в указанное время."
        )
        from scheduler import schedule_auction_start
        schedule_auction_start(context.job_queue, auction_id, start_dt, context)
        return

    await db.update_auction_status(auction_id, "active")

    # убираем отложенный авто-старт, если он был запланирован
    jobs = context.job_queue.get_jobs_by_name(f"auction_start_{auction_id}")
    for j in jobs:
        j.schedule_removal()

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
            chat_id=channel_id,
            photo=auction["photo_id"],
            caption=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_participate_keyboard(auction_id),
        )
    else:
        msg = await context.bot.send_message(
            chat_id=channel_id,
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


# ---------- Список розыгрышей ----------

async def cb_my_auctions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auctions = await db.get_all_auctions_by_admin(query.from_user.id)
    if not auctions:
        await query.edit_message_text(
            "📋 У вас пока нет розыгрышей.\n\nНажмите «Создать розыгрыш» чтобы начать."
        )
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
    if not auction:
        await query.edit_message_text("❌ Розыгрыш не найден.")
        return
    text = _build_auction_text(auction)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_auction_detail_keyboard(auction_id, auction["status"]),
    )


# ---------- Ставки / победитель ----------

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
        chat_id=auction["channel_id"],
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
            chat_id=auction["channel_id"],
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
        chat_id=auction["channel_id"],
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    await query.edit_message_text(
        f"✅ Розыгрыш завершён досрочно. Победитель: @{top_bid['username'] or top_bid['user_id']}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_create_auction, pattern="^create_auction$"),
            CallbackQueryHandler(cb_create_auction_for_channel, pattern="^create_auction_ch:"),
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
            CHANNEL_SELECT: [
                CallbackQueryHandler(cb_select_channel, pattern="^channel_select:"),
                CallbackQueryHandler(cb_cancel_create, pattern="^cancel_dialog$"),
            ],
            PREVIEW: [
                CallbackQueryHandler(cb_preview, pattern="^preview:"),
                CallbackQueryHandler(cb_start_auction, pattern="^start_auction:"),
                CallbackQueryHandler(cb_cancel_auction, pattern="^cancel_auction:"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )