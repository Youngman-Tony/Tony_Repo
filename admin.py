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

TITLE, DESCRIPTION, MIN_BID, STEP, START_DATE, START_TIME, END_DATE, END_TIME, PHOTO, CHANNEL_SELECT, PREVIEW = range(11)


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
            f"рџ‘‹ РџСЂРёРІРµС‚, {user.first_name}!\n\n"
            f"Р’С‹ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅС‹ РєР°Рє РѕСЂРіР°РЅРёР·Р°С‚РѕСЂ СЂРѕР·С‹РіСЂС‹С€РµР№.\n\n"
            f"Р§С‚РѕР±С‹ РЅР°С‡Р°С‚СЊ, РґРѕР±Р°РІСЊС‚Рµ Р±РѕС‚Р° РІ СЃРІРѕР№ РєР°РЅР°Р» РєР°Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°, "
            f"Р·Р°С‚РµРј РїРѕРґРєР»СЋС‡РёС‚Рµ РєР°РЅР°Р» С‡РµСЂРµР· РјРµРЅСЋ В«РњРѕРё РєР°РЅР°Р»С‹В»."
        )
    await update.message.reply_text(
        "рџ‘‹ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ:",
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "рџ‘‹ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ:",
        reply_markup=get_main_menu_keyboard()
    )


# ---------- РљР°РЅР°Р»С‹ ----------

async def cb_my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channels = await db.get_channels_by_admin(query.from_user.id)
    if not channels:
        await query.edit_message_text(
            "рџ“ў РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ РїРѕРґРєР»СЋС‡С‘РЅРЅС‹С… РєР°РЅР°Р»РѕРІ.\n\n"
            "Р”РѕР±Р°РІСЊС‚Рµ Р±РѕС‚Р° РІ РєР°РЅР°Р» РєР°Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°, Р·Р°С‚РµРј РЅР°Р¶РјРёС‚Рµ "
            "В«вћ• Р”РѕР±Р°РІРёС‚СЊ РєР°РЅР°Р»В» Рё РїРµСЂРµС€Р»РёС‚Рµ Р»СЋР±РѕРµ СЃРѕРѕР±С‰РµРЅРёРµ РёР· РєР°РЅР°Р»Р°.",
            reply_markup=get_channels_keyboard(channels)
        )
    else:
        await query.edit_message_text(
            "рџ“ў Р’Р°С€Рё РєР°РЅР°Р»С‹:",
            reply_markup=get_channels_keyboard(channels)
        )


async def cb_channel_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    channel = await db.get_channel(query.from_user.id, channel_id)
    if not channel:
        await query.edit_message_text("вќЊ РљР°РЅР°Р» РЅРµ РЅР°Р№РґРµРЅ.")
        return
    await query.edit_message_text(
        f"рџ“ў <b>{channel['title'] or channel['username'] or channel['channel_id']}</b>\n\n"
        f"РљР°РЅР°Р» РїРѕРґРєР»СЋС‡С‘РЅ. РўРµРїРµСЂСЊ РјРѕР¶РЅРѕ СЃРѕР·РґР°РІР°С‚СЊ СЂРѕР·С‹РіСЂС‹С€Рё.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_channel_detail_keyboard(channel_id),
    )


async def cb_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "рџ“ў <b>РџРѕРґРєР»СЋС‡РµРЅРёРµ РєР°РЅР°Р»Р°</b>\n\n"
        "1. Р”РѕР±Р°РІСЊС‚Рµ Р±РѕС‚Р° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј РІ РІР°С€ РєР°РЅР°Р»\n"
        "   (РЈРїСЂР°РІР»РµРЅРёРµ в†’ РђРґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂС‹ в†’ Р”РѕР±Р°РІРёС‚СЊ в†’ @Tony_auction_bot)\n"
        "2. Р’РІРµРґРёС‚Рµ СЃСЋРґР° <b>@username РєР°РЅР°Р»Р°</b>\n\n"
        "рџ”’ Р”Р»СЏ РїСЂРёРІР°С‚РЅРѕРіРѕ РєР°РЅР°Р»Р° вЂ” РїСЂРёС€Р»РёС‚Рµ РµРіРѕ С‡РёСЃР»РѕРІРѕР№ ID.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("рџ”™ РќР°Р·Р°Рґ", callback_data="my_channels")]
        ]),
    )
    context.user_data["awaiting_channel_input"] = True


async def handle_channel_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_channel_input"):
        return

    text = update.message.text.strip().lstrip("@")

    context.user_data["pending_channel"] = text
    context.user_data["awaiting_channel_input"] = False

    await update.message.reply_text("рџ”Ќ РџСЂРѕРІРµСЂСЏСЋ РґРѕСЃС‚СѓРї Рє РєР°РЅР°Р»Сѓ...")
    await _check_channel(context, update.effective_user.id, chat_id_sender=update.message.chat.id, destination=update.message, input_text=text)


async def cb_check_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = context.user_data.get("pending_channel")
    if not text:
        await query.edit_message_text("вљ™пёЏ РЎРЅР°С‡Р°Р»Р° РІРІРµРґРёС‚Рµ @username РєР°РЅР°Р»Р°. РќР°Р¶РјРёС‚Рµ В«вћ• Р”РѕР±Р°РІРёС‚СЊ РєР°РЅР°Р»В» Рё РїРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.")
        return
    await query.edit_message_text("рџ”Ќ РџСЂРѕРІРµСЂСЏСЋ...")
    await _check_channel(context, query.from_user.id, chat_id_sender=query.message.chat.id, destination=query, input_text=text)


async def _check_channel(context: ContextTypes.DEFAULT_TYPE, user_id, chat_id_sender, destination, input_text):
    try:
        if input_text.lstrip("-").isdigit():
            chat_id = int(input_text)
        else:
            chat = await context.bot.get_chat(
                input_text if input_text.startswith("@") else f"@{input_text}"
            )
            chat_id = chat.id

        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        bot_is_admin = bot_member.status in ("administrator", "creator")

        user_member = await context.bot.get_chat_member(chat_id, user_id)
        user_is_admin = user_member.status in ("administrator", "creator")
    except Exception:
        bot_is_admin = False
        user_is_admin = False
        chat_id = None

    if not chat_id:
        text = (
            "вќЊ <b>РќРµ СѓРґР°Р»РѕСЃСЊ РЅР°Р№С‚Рё РєР°РЅР°Р».</b>\n\n"
            "РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ @username СѓРєР°Р·Р°РЅ РІРµСЂРЅРѕ.\n"
            "Р”Р»СЏ РїСЂРёРІР°С‚РЅРѕРіРѕ РєР°РЅР°Р»Р° РёСЃРїРѕР»СЊР·СѓР№С‚Рµ С‡РёСЃР»РѕРІРѕР№ ID.",
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("рџ”ґ РџРѕРїСЂРѕР±РѕРІР°С‚СЊ СЃРЅРѕРІР°", callback_data="add_channel")],
        ])
        if hasattr(destination, "edit_message_text"):
            await destination.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await destination.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    if not bot_is_admin:
        text = (
            f"вљ пёЏ <b>Р‘РѕС‚ РЅРµ СЏРІР»СЏРµС‚СЃСЏ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј РєР°РЅР°Р»Р°.</b>\n\n"
            f"1. РћС‚РєСЂРѕР№С‚Рµ РєР°РЅР°Р»\n"
            f"2. РЈРїСЂР°РІР»РµРЅРёРµ в†’ РђРґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂС‹ в†’ Р”РѕР±Р°РІРёС‚СЊ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°\n"
            f"3. Р’С‹Р±РµСЂРёС‚Рµ Р±РѕС‚Р° Рё РґР°Р№С‚Рµ РїСЂР°РІР°\n"
            f"4. РќР°Р¶РјРёС‚Рµ В«вњ… РџСЂРѕРІРµСЂРёС‚СЊВ» РµС‰Рµ СЂР°Р·"
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("вњ… РџСЂРѕРІРµСЂРёС‚СЊ", callback_data="check_channel")],
            [InlineKeyboardButton("рџ”™ РќР°Р·Р°Рґ", callback_data="my_channels")],
        ])
        if hasattr(destination, "edit_message_text"):
            await destination.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await destination.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    if not user_is_admin:
        text = (
            f"вќЊ <b>Р’С‹ РЅРµ СЏРІР»СЏРµС‚РµСЃСЊ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј СЌС‚РѕРіРѕ РєР°РЅР°Р»Р°.</b>\n\n"
            f"РџРѕРґРєР»СЋС‡Р°С‚СЊ РјРѕР¶РЅРѕ С‚РѕР»СЊРєРѕ РєР°РЅР°Р»С‹, РіРґРµ РІС‹ РёРјРµРµС‚Рµ РїСЂР°РІР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР°."
        )
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("рџ”™ РќР°Р·Р°Рґ", callback_data="my_channels")],
        ])
        if hasattr(destination, "edit_message_text"):
            await destination.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await destination.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return

    chat = await context.bot.get_chat(chat_id)
    await db.add_channel(
        admin_id=user_id,
        channel_id=chat_id,
        title=chat.title,
        username=chat.username,
    )

    name = chat.title or (f"@{chat.username}" if chat.username else str(chat_id))
    text = (
        f"вњ… <b>РљР°РЅР°Р» РїРѕРґРєР»СЋС‡С‘РЅ!</b>\n\n"
        f"рџ“ў {name}\n\n"
        f"РўРµРїРµСЂСЊ РјРѕР¶РЅРѕ СЃРѕР·РґР°РІР°С‚СЊ СЂРѕР·С‹РіСЂС‹С€Рё."
    )
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("рџЋЃ РЎРѕР·РґР°С‚СЊ СЂРѕР·С‹РіСЂС‹С€", callback_data=f"create_auction_ch:{chat_id}")],
        [InlineKeyboardButton("рџ“ў РњРѕРё РєР°РЅР°Р»С‹", callback_data="my_channels")],
    ])
    if hasattr(destination, "edit_message_text"):
        await destination.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await destination.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def cb_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    await db.remove_channel(query.from_user.id, channel_id)
    channels = await db.get_channels_by_admin(query.from_user.id)
    text = "рџ“ў Р’Р°С€Рё РєР°РЅР°Р»С‹:" if channels else "рџ“ў РљР°РЅР°Р»РѕРІ РЅРµС‚.\n\nРќР°Р¶РјРёС‚Рµ В«вћ• Р”РѕР±Р°РІРёС‚СЊ РєР°РЅР°Р»В» С‡С‚РѕР±С‹ РїРѕРґРєР»СЋС‡РёС‚СЊ."
    await query.edit_message_text(text, reply_markup=get_channels_keyboard(channels))


# ---------- РЎРѕР·РґР°РЅРёРµ СЂРѕР·С‹РіСЂС‹С€Р° ----------

async def cb_create_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("рџ“ќ Р’РІРµРґРёС‚Рµ РѕРїРёСЃР°РЅРёРµ (РЅР°Р·РІР°РЅРёРµ) СЂРѕР·С‹РіСЂС‹С€Р°:")
    return TITLE


async def cb_create_auction_for_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_id = int(query.data.split(":")[1])
    context.user_data["channel_id"] = channel_id
    await query.edit_message_text("рџ“ќ Р’РІРµРґРёС‚Рµ РѕРїРёСЃР°РЅРёРµ (РЅР°Р·РІР°РЅРёРµ) СЂРѕР·С‹РіСЂС‹С€Р°:")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text(
        "рџ“ќ РўРµРїРµСЂСЊ РІРІРµРґРёС‚Рµ РѕРїРёСЃР°РЅРёРµ СЂРѕР·С‹РіСЂС‹С€Р° (С‡С‚Рѕ СЂР°Р·С‹РіСЂС‹РІР°РµС‚СЃСЏ, СѓСЃР»РѕРІРёСЏ):"
    )
    return DESCRIPTION


async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("рџ’° Р’РІРµРґРёС‚Рµ РјРёРЅРёРјР°Р»СЊРЅСѓСЋ СЃС‚Р°РІРєСѓ (РІ СЂСѓР±Р»СЏС…):")
    return MIN_BID


async def get_min_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("Р’РІРµРґРёС‚Рµ РїРѕР»РѕР¶РёС‚РµР»СЊРЅРѕРµ С‡РёСЃР»Рѕ:")
        return MIN_BID
    context.user_data["min_bid"] = int(text)
    await update.message.reply_text("рџ“€ Р’РІРµРґРёС‚Рµ РјРёРЅРёРјР°Р»СЊРЅС‹Р№ С€Р°Рі СѓРІРµР»РёС‡РµРЅРёСЏ СЃС‚Р°РІРєРё (РІ СЂСѓР±Р»СЏС…):")
    return STEP


async def get_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("Р’РІРµРґРёС‚Рµ РїРѕР»РѕР¶РёС‚РµР»СЊРЅРѕРµ С‡РёСЃР»Рѕ:")
        return STEP
    context.user_data["step"] = int(text)
    await update.message.reply_text("рџ“… Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РЅР°С‡Р°Р»Р° СЂРѕР·С‹РіСЂС‹С€Р° РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:")
    return START_DATE


async def get_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:")
        return START_DATE
    context.user_data["start_date"] = text
    await update.message.reply_text("вЏ° Р’РІРµРґРёС‚Рµ РІСЂРµРјСЏ РЅР°С‡Р°Р»Р° РІ С„РѕСЂРјР°С‚Рµ Р§Р§:РњРњ:")
    return START_TIME


async def get_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await update.message.reply_text("РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ РІСЂРµРјСЏ РІ С„РѕСЂРјР°С‚Рµ Р§Р§:РњРњ:")
        return START_TIME
    context.user_data["start_time"] = text
    await update.message.reply_text("рџ“… Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ Р·Р°РІРµСЂС€РµРЅРёСЏ СЂРѕР·С‹РіСЂС‹С€Р° РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:")
    return END_DATE


async def get_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:")
        return END_DATE
    context.user_data["end_date"] = text
    await update.message.reply_text("вЏ° Р’РІРµРґРёС‚Рµ РІСЂРµРјСЏ Р·Р°РІРµСЂС€РµРЅРёСЏ РІ С„РѕСЂРјР°С‚Рµ Р§Р§:РњРњ:")
    return END_TIME


async def get_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await update.message.reply_text("РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚. Р’РІРµРґРёС‚Рµ РІСЂРµРјСЏ РІ С„РѕСЂРјР°С‚Рµ Р§Р§:РњРњ:")
        return END_TIME
    context.user_data["end_time"] = text
    await update.message.reply_text("рџ–ј РћС‚РїСЂР°РІСЊС‚Рµ РёР·РѕР±СЂР°Р¶РµРЅРёРµ РґР»СЏ СЂРѕР·С‹РіСЂС‹С€Р° (РёР»Рё /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ):")
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
            "вќЊ Р’СЂРµРјСЏ Р·Р°РІРµСЂС€РµРЅРёСЏ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РїРѕР·Р¶Рµ РІСЂРµРјРµРЅРё РЅР°С‡Р°Р»Р°. РџРѕРїСЂРѕР±СѓР№С‚Рµ СЃРЅРѕРІР°.\n"
            "Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РЅР°С‡Р°Р»Р° РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:"
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
            "вќЊ Р’СЂРµРјСЏ Р·Р°РІРµСЂС€РµРЅРёСЏ РґРѕР»Р¶РЅРѕ Р±С‹С‚СЊ РїРѕР·Р¶Рµ РІСЂРµРјРµРЅРё РЅР°С‡Р°Р»Р°.\n"
            "Р’РІРµРґРёС‚Рµ РґР°С‚Сѓ РЅР°С‡Р°Р»Р° РІ С„РѕСЂРјР°С‚Рµ Р”Р”.РњРњ.Р“Р“Р“Р“:"
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
            text="вљ пёЏ РЎРЅР°С‡Р°Р»Р° РїРѕРґРєР»СЋС‡РёС‚Рµ РєР°РЅР°Р»!\n\n"
                 "РњРµРЅСЋ В«рџ“ў РњРѕРё РєР°РЅР°Р»С‹В» в†’ В«вћ• Р”РѕР±Р°РІРёС‚СЊ РєР°РЅР°Р»В» в†’ РїРµСЂРµС€Р»РёС‚Рµ "
                 "СЃРѕРѕР±С‰РµРЅРёРµ РёР· РєР°РЅР°Р»Р°, РІ РєРѕС‚РѕСЂРѕРј С…РѕС‚РёС‚Рµ РїСЂРѕРІРѕРґРёС‚СЊ СЂРѕР·С‹РіСЂС‹С€.",
            reply_markup=get_main_menu_keyboard(),
        )
        return ConversationHandler.END

    if len(channels) == 1:
        context.user_data["channel_id"] = channels[0]["channel_id"]
        return await _create_auction_record(user_id, context)

    await context.bot.send_message(
        chat_id=user_id,
        text="рџ“ў Р’С‹Р±РµСЂРёС‚Рµ РєР°РЅР°Р» РґР»СЏ СЂРѕР·С‹РіСЂС‹С€Р°:",
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
    await query.edit_message_text("вќЊ РЎРѕР·РґР°РЅРёРµ СЂРѕР·С‹РіСЂС‹С€Р° РѕС‚РјРµРЅРµРЅРѕ.", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END


async def _create_auction_record(user_id, context, query_message=None):
    auction_id = await db.create_auction(
        admin_id=user_id,
        title=context.user_data["title"],
        description=context.user_data.get("description"),
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


def _build_auction_text(auction):
    start = datetime.fromisoformat(auction["start_time"]).strftime("%d.%m.%Y %H:%M")
    end = datetime.fromisoformat(auction["end_time"]).strftime("%d.%m.%Y %H:%M")
    status_map = {"draft": "рџ“ќ Р§РµСЂРЅРѕРІРёРє", "scheduled": "вЏ° Р—Р°РїР»Р°РЅРёСЂРѕРІР°РЅ", "active": "рџџў РђРєС‚РёРІРµРЅ", "finished": "рџ”ґ Р—Р°РІРµСЂС€С‘РЅ", "cancelled": "вќЊ РћС‚РјРµРЅС‘РЅ"}
    desc = f"\nрџ“‹ РћРїРёСЃР°РЅРёРµ: <b>{auction['description']}</b>\n" if auction["description"] else ""
    return (
        f"рџЋЇ <b>{auction['title']}</b>\n\n"
        f"{desc}"
        f"рџ’° РњРёРЅРёРјР°Р»СЊРЅР°СЏ СЃС‚Р°РІРєР°: <b>{auction['min_bid']} СЂСѓР±.</b>\n"
        f"рџ“€ РЁР°Рі СѓРІРµР»РёС‡РµРЅРёСЏ: <b>{auction['step']} СЂСѓР±.</b>\n\n"
        f"рџ“… РќР°С‡Р°Р»Рѕ: <b>{start}</b>\n"
        f"рџ“… Р—Р°РІРµСЂС€РµРЅРёРµ: <b>{end}</b>\n\n"
        f"РЎС‚Р°С‚СѓСЃ: {status_map.get(auction['status'], auction['status'])}"
    )


# ---------- РџСЂРµРґРїСЂРѕСЃРјРѕС‚СЂ / Р·Р°РїСѓСЃРє ----------

async def cb_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)
    if not auction:
        await query.edit_message_text("вќЊ Р РѕР·С‹РіСЂС‹С€ РЅРµ РЅР°Р№РґРµРЅ.")
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
        await query.edit_message_text("вќЊ Р РѕР·С‹РіСЂС‹С€ РЅРµ РЅР°Р№РґРµРЅ.")
        return

    if auction["status"] not in ("draft", "scheduled"):
        await query.edit_message_text("вќЊ Р­С‚РѕС‚ СЂРѕР·С‹РіСЂС‹С€ СѓР¶Рµ Р·Р°РїСѓС‰РµРЅ РёР»Рё Р·Р°РІРµСЂС€С‘РЅ.")
        return

    channel_id = auction["channel_id"]
    start_dt = datetime.fromisoformat(auction["start_time"])
    end_dt = datetime.fromisoformat(auction["end_time"])
    now = datetime.now()

    if start_dt > now:
        await db.update_auction_status(auction_id, "scheduled")
        await query.edit_message_text(
            f"вЏ° Р РѕР·С‹РіСЂС‹С€ Р·Р°РїР»Р°РЅРёСЂРѕРІР°РЅ РЅР° {start_dt.strftime('%d.%m.%Y %H:%M')}. "
            f"Р‘РѕС‚ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё РѕРїСѓР±Р»РёРєСѓРµС‚ РµРіРѕ РІ РєР°РЅР°Р»Рµ РІ СѓРєР°Р·Р°РЅРЅРѕРµ РІСЂРµРјСЏ."
        )
        from scheduler import schedule_auction_start
        schedule_auction_start(context.job_queue, auction_id, start_dt)
        return

    await db.update_auction_status(auction_id, "active")

    # СѓР±РёСЂР°РµРј РѕС‚Р»РѕР¶РµРЅРЅС‹Р№ Р°РІС‚Рѕ-СЃС‚Р°СЂС‚, РµСЃР»Рё РѕРЅ Р±С‹Р» Р·Р°РїР»Р°РЅРёСЂРѕРІР°РЅ
    jobs = context.job_queue.get_jobs_by_name(f"auction_start_{auction_id}")
    for j in jobs:
        j.schedule_removal()

    desc_part = f"рџ“‹ <b>{auction['description']}</b>\n\n" if auction["description"] else ""
    channel_text = (
        f"рџЋЇ <b>Р РћР—Р«Р“Р Р«РЁ Р—РђРџРЈР©Р•Рќ!</b>\n\n"
        f"рџЋЃ <b>{auction['title']}</b>\n\n"
        f"{desc_part}"
        f"рџ’° РњРёРЅРёРјР°Р»СЊРЅР°СЏ СЃС‚Р°РІРєР°: <b>{auction['min_bid']} СЂСѓР±.</b>\n"
        f"рџ“€ РЁР°Рі: <b>{auction['step']} СЂСѓР±.</b>\n\n"
        f"вЏ° Р—Р°РІРµСЂС€РµРЅРёРµ: <b>{end_dt.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"РќР°Р¶РјРёС‚Рµ В«РЈС‡Р°СЃС‚РІРѕРІР°С‚СЊВ», С‡С‚РѕР±С‹ СЃРґРµР»Р°С‚СЊ СЃС‚Р°РІРєСѓ!"
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

    await query.edit_message_text("вњ… Р РѕР·С‹РіСЂС‹С€ Р·Р°РїСѓС‰РµРЅ Рё РѕРїСѓР±Р»РёРєРѕРІР°РЅ РІ РєР°РЅР°Р»Рµ!")

    from scheduler import schedule_auction_end
    schedule_auction_end(context.job_queue, auction_id, end_dt)


async def cb_cancel_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    await db.update_auction_status(auction_id, "cancelled")
    await query.edit_message_text("вќЊ Р РѕР·С‹РіСЂС‹С€ РѕС‚РјРµРЅС‘РЅ.")


# ---------- РЎРїРёСЃРѕРє СЂРѕР·С‹РіСЂС‹С€РµР№ ----------

async def cb_my_auctions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auctions = await db.get_all_auctions_by_admin(query.from_user.id)
    if not auctions:
        await query.edit_message_text(
            "рџ“‹ РЈ РІР°СЃ РїРѕРєР° РЅРµС‚ СЂРѕР·С‹РіСЂС‹С€РµР№.\n\nРќР°Р¶РјРёС‚Рµ В«РЎРѕР·РґР°С‚СЊ СЂРѕР·С‹РіСЂС‹С€В» С‡С‚РѕР±С‹ РЅР°С‡Р°С‚СЊ."
        )
        return
    await query.edit_message_text(
        "рџ“‹ Р’Р°С€Рё СЂРѕР·С‹РіСЂС‹С€Рё:",
        reply_markup=get_admin_auctions_keyboard(auctions)
    )


async def cb_admin_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    auction = await db.get_auction(auction_id)
    if not auction:
        await query.edit_message_text("вќЊ Р РѕР·С‹РіСЂС‹С€ РЅРµ РЅР°Р№РґРµРЅ.")
        return
    text = _build_auction_text(auction)
    await query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_auction_detail_keyboard(auction_id, auction["status"]),
    )


# ---------- РЎС‚Р°РІРєРё / РїРѕР±РµРґРёС‚РµР»СЊ ----------

async def cb_view_bids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    auction_id = int(query.data.split(":")[1])
    bids = await db.get_bids_for_auction(auction_id)
    if not bids:
        await query.edit_message_text("рџ“Љ РЎС‚Р°РІРѕРє РїРѕРєР° РЅРµС‚.")
        return
    text = "рџ“Љ <b>РЎС‚Р°РІРєРё (РїРѕ СѓР±С‹РІР°РЅРёСЋ):</b>\n\n"
    for i, bid in enumerate(bids, 1):
        text += f"{i}. @{bid['username'] or 'РЅРµС‚_СЋР·РµСЂР°'} вЂ” <b>{bid['amount']} СЂСѓР±.</b>\n"
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
        await query.edit_message_text("вќЊ РЎС‚Р°РІРєР° РЅРµ РЅР°Р№РґРµРЅР°.")
        return

    await db.set_winner(auction_id, winning_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    auction = await db.get_auction(auction_id)

    winner_text = (
        f"рџЏ† <b>РџРћР‘Р•Р”РРўР•Р›Р¬ Р РћР—Р«Р“Р Р«РЁРђ!</b>\n\n"
        f"рџЋЃ {auction['title']}\n\n"
        f"РџРѕР±РµРґРёС‚РµР»СЊ: @{winning_bid['username'] or winning_bid['user_id']}\n"
        f"РЎС‚Р°РІРєР°: <b>{winning_bid['amount']} СЂСѓР±.</b>\n\n"
        f"Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РїСЂРёР·Р° РѕР±СЂР°С‚РёС‚РµСЃСЊ Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ РєР°РЅР°Р»Р°."
    )

    await context.bot.send_message(
        chat_id=auction["channel_id"],
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    await query.edit_message_text(f"вњ… РџРѕР±РµРґРёС‚РµР»СЊ РЅР°Р·РЅР°С‡РµРЅ: @{winning_bid['username'] or winning_bid['user_id']}")


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
            text=f"рџ”ґ Р РѕР·С‹РіСЂС‹С€ В«{auction['title']}В» Р·Р°РІРµСЂС€С‘РЅ РґРѕСЃСЂРѕС‡РЅРѕ.\n"
                 f"РЎС‚Р°РІРѕРє РЅРµ Р±С‹Р»Рѕ, РїРѕР±РµРґРёС‚РµР»СЊ РЅРµ РѕРїСЂРµРґРµР»С‘РЅ.",
            parse_mode=ParseMode.HTML,
        )
        await query.edit_message_text("вњ… Р РѕР·С‹РіСЂС‹С€ Р·Р°РІРµСЂС€С‘РЅ (Р±РµР· СЃС‚Р°РІРѕРє).")
        return

    await db.set_winner(auction_id, top_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    winner_text = (
        f"рџЏ† <b>РџРћР‘Р•Р”РРўР•Р›Р¬ Р РћР—Р«Р“Р Р«РЁРђ!</b>\n\n"
        f"рџЋЃ {auction['title']}\n\n"
        f"РџРѕР±РµРґРёС‚РµР»СЊ: @{top_bid['username'] or top_bid['user_id']}\n"
        f"РЎС‚Р°РІРєР°: <b>{top_bid['amount']} СЂСѓР±.</b>\n\n"
        f"Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РїСЂРёР·Р° РѕР±СЂР°С‚РёС‚РµСЃСЊ Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ РєР°РЅР°Р»Р°."
    )

    await context.bot.send_message(
        chat_id=auction["channel_id"],
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    await query.edit_message_text(
        f"вњ… Р РѕР·С‹РіСЂС‹С€ Р·Р°РІРµСЂС€С‘РЅ РґРѕСЃСЂРѕС‡РЅРѕ. РџРѕР±РµРґРёС‚РµР»СЊ: @{top_bid['username'] or top_bid['user_id']}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Р”РµР№СЃС‚РІРёРµ РѕС‚РјРµРЅРµРЅРѕ.")
    return ConversationHandler.END


def get_admin_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_create_auction, pattern="^create_auction$"),
            CallbackQueryHandler(cb_create_auction_for_channel, pattern="^create_auction_ch:"),
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
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