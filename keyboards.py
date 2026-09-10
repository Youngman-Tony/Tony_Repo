from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Создать розыгрыш", callback_data="create_auction")],
        [InlineKeyboardButton("📢 Мои каналы", callback_data="my_channels")],
        [InlineKeyboardButton("📋 Мои розыгрыши", callback_data="my_auctions")],
    ])


def get_channels_keyboard(channels):
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"📢 {ch['title'] or ch['username'] or ch['channel_id']}",
                callback_data=f"channel:{ch['channel_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("➕ Добавить канал", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


def get_channel_detail_keyboard(channel_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 Создать розыгрыш", callback_data=f"create_auction_ch:{channel_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"remove_channel:{channel_id}"),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="my_channels")],
    ])


def get_auction_preview_keyboard(auction_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Запустить", callback_data=f"start_auction:{auction_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_auction:{auction_id}")],
    ])


from config import BOT_USERNAME


def get_participate_keyboard(auction_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎯 Участвовать",
            url=f"https://t.me/{BOT_USERNAME}?start=auction_{auction_id}",
        )],
    ])


def get_channel_select_keyboard(channels):
    buttons = []
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(
                f"📢 {ch['title'] or ch['username'] or ch['channel_id']}",
                callback_data=f"channel_select:{ch['channel_id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 Отменить", callback_data="cancel_dialog")])
    return InlineKeyboardMarkup(buttons)


def get_bid_keyboard(auction_id, current_amount, step):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📈 +{step} руб.", callback_data=f"increase:{auction_id}")],
        [InlineKeyboardButton("✅ Принять ставку", callback_data=f"accept_bid:{auction_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu")],
    ])


def get_admin_auctions_keyboard(auctions):
    buttons = []
    for auction in auctions:
        status_emoji = {"draft": "📝", "scheduled": "⏰", "active": "🟢", "finished": "🔴", "cancelled": "❌"}.get(auction["status"], "❓")
        buttons.append([
            InlineKeyboardButton(
                f"{status_emoji} #{auction['id']} - {auction['title'][:30]}",
                callback_data=f"admin_auction:{auction['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(buttons)


def get_admin_auction_detail_keyboard(auction_id, status):
    buttons = []
    if status == "draft":
        buttons = [
            [
                InlineKeyboardButton("🚀 Запустить", callback_data=f"start_auction:{auction_id}"),
            ],
            [InlineKeyboardButton("❌ Удалить", callback_data=f"cancel_auction:{auction_id}")],
        ]
    elif status == "scheduled":
        buttons = [
            [InlineKeyboardButton("🚀 Запустить сейчас", callback_data=f"start_auction:{auction_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_auction:{auction_id}")],
        ]
    elif status == "active":
        buttons = [
            [InlineKeyboardButton("📊 Ставки", callback_data=f"view_bids:{auction_id}")],
            [InlineKeyboardButton("⏹ Завершить досрочно", callback_data=f"finish_early:{auction_id}")],
        ]
    elif status == "finished":
        buttons = [
            [InlineKeyboardButton("📊 Все ставки", callback_data=f"view_bids:{auction_id}")],
            [InlineKeyboardButton("🏆 Назначить победителя", callback_data=f"select_winner:{auction_id}")],
        ]
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="my_auctions")])
    return InlineKeyboardMarkup(buttons)


def get_bids_keyboard(bids, auction_id):
    buttons = []
    for bid in bids:
        buttons.append([
            InlineKeyboardButton(
                f"@{bid['username'] or 'нет_юзера'} - {bid['amount']} руб.",
                callback_data=f"select_winner_bid:{auction_id}:{bid['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"admin_auction:{auction_id}")])
    return InlineKeyboardMarkup(buttons)