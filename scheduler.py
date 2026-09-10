import logging
from datetime import datetime

from telegram.constants import ParseMode

import database as db
from keyboards import get_participate_keyboard

logger = logging.getLogger(__name__)


async def auction_start_callback(context):
    job = context.job
    auction_id = job.data

    auction = await db.get_auction(auction_id)
    if not auction or auction["status"] != "scheduled":
        return

    await _publish_auction(context, auction)


async def _publish_auction(context, auction):
    auction_id = auction["id"]
    start_dt = datetime.fromisoformat(auction["start_time"])
    end_dt = datetime.fromisoformat(auction["end_time"])

    desc_part = f"📋 <b>{auction['description']}</b>\n\n" if auction["description"] else ""
    channel_text = (
        f"🎯 <b>РОЗЫГРЫШ ЗАПУЩЕН!</b>\n\n"
        f"🎁 <b>{auction['title']}</b>\n\n"
        f"{desc_part}"
        f"💰 Минимальная ставка: <b>{auction['min_bid']} руб.</b>\n"
        f"📈 Шаг: <b>{auction['step']} руб.</b>\n\n"
        f"💥 Первая ставка: <b>{auction['min_bid']} руб.</b>\n\n"
        f"⏰ Завершение: <b>{end_dt.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"Нажмите «Участвовать», чтобы сделать ставку!"
    )

    if auction["photo_id"]:
        msg = await context.bot.send_photo(
            chat_id=auction["channel_id"],
            photo=auction["photo_id"],
            caption=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_participate_keyboard(auction_id),
        )
    else:
        msg = await context.bot.send_message(
            chat_id=auction["channel_id"],
            text=channel_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_participate_keyboard(auction_id),
        )

    await db.update_auction_status(auction_id, "active", channel_message_id=msg.message_id)

    schedule_auction_end(context.job_queue, auction_id, end_dt)


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
            chat_id=auction["channel_id"],
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
        chat_id=auction["channel_id"],
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


def schedule_auction_end(job_queue, auction_id, end_dt):
    now = datetime.now()
    delay = (end_dt - now).total_seconds()
    job_queue.run_once(auction_end_callback, when=max(delay, 0), data=auction_id, name=f"auction_end_{auction_id}")


def schedule_auction_start(job_queue, auction_id, start_dt):
    now = datetime.now()
    delay = (start_dt - now).total_seconds()
    job_queue.run_once(auction_start_callback, when=max(delay, 0), data=auction_id, name=f"auction_start_{auction_id}")


async def restore_scheduled_jobs(app):
    auctions = await db.get_all_auctions_by_status(["active", "scheduled"])
    now = datetime.now()
    job_queue = app.job_queue

    for auction in auctions:
        if auction["status"] == "scheduled":
            start_dt = datetime.fromisoformat(auction["start_time"])
            if start_dt > now:
                schedule_auction_start(job_queue, auction["id"], start_dt)
                continue
            await _publish_auction(app, auction)
            continue

        if auction["status"] == "active":
            end_dt = datetime.fromisoformat(auction["end_time"])
            if end_dt > now:
                schedule_auction_end(job_queue, auction["id"], end_dt)