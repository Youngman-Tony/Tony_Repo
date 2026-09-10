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

    desc_part = f"рџ“‹ <b>{auction['description']}</b>\n\n" if auction["description"] else ""
    channel_text = (
        f"рџЋЇ <b>Р РћР—Р«Р“Р Р«РЁ Р—РђРџРЈР©Р•Рќ!</b>\n\n"
        f"рџЋЃ <b>{auction['title']}</b>\n\n"
        f"{desc_part}"
        f"рџ’° РњРёРЅРёРјР°Р»СЊРЅР°СЏ СЃС‚Р°РІРєР°: <b>{auction['min_bid']} СЂСѓР±.</b>\n"
        f"рџ“€ РЁР°Рі: <b>{auction['step']} СЂСѓР±.</b>\n\n"
        f"рџ’Ґ РџРµСЂРІР°СЏ СЃС‚Р°РІРєР°: <b>{auction['min_bid']} СЂСѓР±.</b>\n\n"
        f"вЏ° Р—Р°РІРµСЂС€РµРЅРёРµ: <b>{end_dt.strftime('%d.%m.%Y %H:%M')}</b>\n\n"
        f"РќР°Р¶РјРёС‚Рµ В«РЈС‡Р°СЃС‚РІРѕРІР°С‚СЊВ», С‡С‚РѕР±С‹ СЃРґРµР»Р°С‚СЊ СЃС‚Р°РІРєСѓ!"
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
                f"рџ”ґ <b>Р РћР—Р«Р“Р Р«РЁ Р—РђР’Р•Р РЁРЃРќ</b>\n\n"
                f"рџЋЃ {auction['title']}\n\n"
                f"РЎС‚Р°РІРѕРє РЅРµ Р±С‹Р»Рѕ. РџРѕР±РµРґРёС‚РµР»СЊ РЅРµ РѕРїСЂРµРґРµР»С‘РЅ."
            ),
            parse_mode=ParseMode.HTML,
        )
        return

    await db.set_winner(auction_id, top_bid["user_id"])
    await db.update_auction_status(auction_id, "finished")

    username = top_bid["username"] or str(top_bid["user_id"])
    winner_text = (
        f"рџЏ† <b>РџРћР‘Р•Р”РРўР•Р›Р¬ Р РћР—Р«Р“Р Р«РЁРђ!</b>\n\n"
        f"рџЋЃ <b>{auction['title']}</b>\n\n"
        f"РџРѕР±РµРґРёС‚РµР»СЊ: @{username}\n"
        f"РЎС‚Р°РІРєР°: <b>{top_bid['amount']} СЂСѓР±.</b>\n\n"
        f"Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РїСЂРёР·Р° РѕР±СЂР°С‚РёС‚РµСЃСЊ Рє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂСѓ РєР°РЅР°Р»Р°."
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
                f"рџЋ‰ <b>РџРѕР·РґСЂР°РІР»СЏРµРј!</b>\n\n"
                f"Р’С‹ РїРѕР±РµРґРёР»Рё РІ СЂРѕР·С‹РіСЂС‹С€Рµ В«{auction['title']}В»!\n"
                f"Р’Р°С€Р° СЃС‚Р°РІРєР°: <b>{top_bid['amount']} СЂСѓР±.</b>\n\n"
                f"Р”Р»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РїСЂРёР·Р° СЃРІСЏР¶РёС‚РµСЃСЊ СЃ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј РєР°РЅР°Р»Р°."
            ),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.warning(f"РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РїСЂР°РІРёС‚СЊ Р›РЎ РїРѕР±РµРґРёС‚РµР»СЋ {top_bid['user_id']}: {e}")


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