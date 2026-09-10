import functools
import logging

from telegram import Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from retry import call_with_retry
from handlers.admin import (
    cmd_start,
    get_admin_conversation_handler,
    cb_my_channels,
    cb_channel_detail,
    cb_add_channel,
    cb_remove_channel,
    handle_channel_input,
    cb_check_channel,
    cb_my_auctions,
    cb_admin_auction,
    cb_preview,
    cb_start_auction,
    cb_cancel_auction,
    cb_view_bids,
    cb_select_winner_bid,
    cb_finish_early,
    back_to_main,
)
from handlers.user import (
    cb_participate,
    cb_increase,
    cb_accept_bid,
    back_to_menu,
)
from scheduler import restore_scheduled_jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# методы Telegram API, вызовы которых оборачиваем в retry
RETRY_METHODS = (
    "send_message",
    "send_photo",
    "edit_message_text",
    "edit_message_media",
    "answer_callback_query",
    "get_chat",
    "get_chat_member",
)


async def error_handler(update, context):
    logger.error("Exception while handling an update:", exc_info=context.error)


def _wrap_bot_methods():
    # ППР: ExtBot запрещает setattr на экземпляре, патчим методы на уровне класса Bot
    for method_name in RETRY_METHODS:
        orig = getattr(Bot, method_name, None)
        if not orig:
            continue

        async def wrapped(self, *args, _orig=orig, **kwargs):
            return await call_with_retry(_orig, self, *args, **kwargs)

        wrapped.__name__ = method_name
        setattr(Bot, method_name, wrapped)


def main():
    _wrap_bot_methods()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_error_handler(error_handler)

    admin_conv = get_admin_conversation_handler()
    app.add_handler(admin_conv)

    app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_channel_input))

    app.add_handler(CallbackQueryHandler(cb_participate, pattern=r"^participate:"))
    app.add_handler(CallbackQueryHandler(cb_increase, pattern=r"^increase:"))
    app.add_handler(CallbackQueryHandler(cb_accept_bid, pattern=r"^accept_bid:"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern=r"^back_to_menu$"))

    app.add_handler(CallbackQueryHandler(cb_my_channels, pattern=r"^my_channels$"))
    app.add_handler(CallbackQueryHandler(cb_channel_detail, pattern=r"^channel:"))
    app.add_handler(CallbackQueryHandler(cb_add_channel, pattern=r"^add_channel$"))
    app.add_handler(CallbackQueryHandler(cb_check_channel, pattern=r"^check_channel$"))
    app.add_handler(CallbackQueryHandler(cb_remove_channel, pattern=r"^remove_channel:"))

    app.add_handler(CallbackQueryHandler(cb_my_auctions, pattern=r"^my_auctions$"))
    app.add_handler(CallbackQueryHandler(cb_admin_auction, pattern=r"^admin_auction:"))
    app.add_handler(CallbackQueryHandler(cb_preview, pattern=r"^preview:"))
    app.add_handler(CallbackQueryHandler(cb_start_auction, pattern=r"^start_auction:"))
    app.add_handler(CallbackQueryHandler(cb_cancel_auction, pattern=r"^cancel_auction:"))
    app.add_handler(CallbackQueryHandler(cb_view_bids, pattern=r"^view_bids:"))
    app.add_handler(CallbackQueryHandler(cb_select_winner_bid, pattern=r"^select_winner_bid:"))
    app.add_handler(CallbackQueryHandler(cb_finish_early, pattern=r"^finish_early:"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern=r"^back_to_main$"))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])


async def post_init(application: Application):
    await init_db()
    await restore_scheduled_jobs(application)
    logger.info("Bot started, DB initialized, jobs restored.")


if __name__ == "__main__":
    main()