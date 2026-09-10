import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from config import BOT_TOKEN
from database import init_db
from handlers.admin import (
    cmd_start,
    get_admin_conversation_handler,
    cb_my_auctions,
    cb_admin_auction,
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


async def post_init(application: Application):
    await init_db()
    await restore_scheduled_jobs(application.job_queue)
    logger.info("Bot started, DB initialized, jobs restored.")


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    admin_conv = get_admin_conversation_handler()
    app.add_handler(admin_conv)

    app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(CallbackQueryHandler(cb_participate, pattern=r"^participate:"))
    app.add_handler(CallbackQueryHandler(cb_increase, pattern=r"^increase:"))
    app.add_handler(CallbackQueryHandler(cb_accept_bid, pattern=r"^accept_bid:"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern=r"^back_to_menu$"))

    app.add_handler(CallbackQueryHandler(cb_my_auctions, pattern=r"^my_auctions$"))
    app.add_handler(CallbackQueryHandler(cb_admin_auction, pattern=r"^admin_auction:"))
    app.add_handler(CallbackQueryHandler(cb_view_bids, pattern=r"^view_bids:"))
    app.add_handler(CallbackQueryHandler(cb_select_winner_bid, pattern=r"^select_winner_bid:"))
    app.add_handler(CallbackQueryHandler(cb_finish_early, pattern=r"^finish_early:"))
    app.add_handler(CallbackQueryHandler(back_to_main, pattern=r"^back_to_main$"))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
