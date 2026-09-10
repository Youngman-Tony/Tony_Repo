import logging
from datetime import datetime

from telegram.constants import ParseMode

import database as db
from config import CHANNEL_ID

logger = logging.getLogger(__name__)


async def auction_end_callback(context):
    job = context.job
    auction_id = job.data

    auction = await db.get_auction(auction_id)
    if not auction or auction["status"] != "active":
        return

    top_bid = await db.get_top_bid(auction_id)

    if not top_bid:
        await db.update_auction_status(auction_id, "finished")
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🔴 <b>РОЗЫГРЫШ ЗАВЕРШЁН</b>\n\n"
                f"🎁 {auction['title']}\n\n"
                f"Ставок не было. Победитель не определён."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    await db.set_winner(auction_id, top_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    username = top_bid["username"] or str(top_bid["user_id"])
    winner_text = (
        f"🏆 <b>ПОБЕДИТЕЛЬ РОЗЫГРЫША!</b>\n\n"
        f"🎁 <b>{auction['title']}</b>\n\n"
        f"Победитель: @{username}\n"
        f"Ставка: <b>{top_bid['amount']} руб.</b>\n\n"
        f"Для получения приза обратитесь к администратору канала."
    )

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=winner_text,
        parse_mode=ParseMode.HTML,
    )

    try:
        await context.bot.send_message(
            chat_id=top_bid["user_id"],
            text=(
                f"🎉 <b>Поздравляем!</b>\n\n"
                f"Вы победили в розыгрыше «{auction['title']}»!\n"
                f"Ваша ставка: <b>{top_bid['amount']} руб.</b>\n\n"
                f"Для получения приза свяжитесь с администратором канала."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить ЛС победителю {top_bid['user_id']}: {e}")


def schedule_auction_end(job_queue, auction_id, end_dt, context):
    now = datetime.now()
    delay = (end_dt - now).total_seconds()

    if delay <= 0:
        job_queue.run_once(auction_end_callback, when=0, data=auction_id, name=f"auction_end_{auction_id}")
    else:
        job_queue.run_once(auction_end_callback, when=delay, data=auction_id, name=f"auction_end_{auction_id}")


async def restore_scheduled_jobs(context):
    auctions = await db.get_active_auctions()
    now = datetime.now()

    for auction in auctions:
        end_dt = datetime.fromisoformat(auction["end_time"])
        if end_dt > now:
            schedule_auction_end(context.job_queue, auction["id"], end_dt, context)
