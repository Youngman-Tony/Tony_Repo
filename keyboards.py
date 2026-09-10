from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Создать розыгрыш", callback_data="create_auction")],
        [InlineKeyboardButton("📋 Мои розыгрыши", callback_data="my_auctions")],
    ])


def get_auction_preview_keyboard(auction_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👁 Предпросмотр", callback_data=f"preview:{auction_id}"),
            InlineKeyboardButton("🚀 Запустить", callback_data=f"start_auction:{auction_id}"),
        ],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_auction:{auction_id}")],
    ])


def get_participate_keyboard(auction_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Участвовать", callback_data=f"participate:{auction_id}")],
    ])


def get_bid_keyboard(auction_id, current_amount, step):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📈 +{step} руб.", callback_data=f"increase:{auction_id}")],
        [InlineKeyboardButton("✅ Принять ставку", callback_data=f"accept_bid:{auction_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_menu")],
    ])


def get_admin_auctions_keyboard(auctions):
    buttons = []
    for auction in auctions:
        status_emoji = {"draft": "📝", "active": "🟢", "finished": "🔴"}.get(auction["status"], "❓")
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
                InlineKeyboardButton("👁 Предпросмотр", callback_data=f"preview:{auction_id}"),
                InlineKeyboardButton("🚀 Запустить", callback_data=f"start_auction:{auction_id}"),
            ],
            [InlineKeyboardButton("❌ Удалить", callback_data=f"cancel_auction:{auction_id}")],
        ]
    elif status == "active":
        buttons = [
            [InlineKeyboardButton("📊 Ставки", callback_data=f"view_bids:{auction_id}")],
            [InlineKeyboardButton("⏹ Завершить досрочно", callback_data=f"finish_early:{auction_id}")],
        ]
    elif status == "finished":
        buttons = [
            [InlineKeyboardButton("📊 Все ставки", callback_data=f"view_bids:{auction_id}")],
            [InlineKeyboardButton("🏅 Назначить победителя", callback_data=f"select_winner:{auction_id}")],
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
