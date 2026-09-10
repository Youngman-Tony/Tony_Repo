import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                min_bid INTEGER NOT NULL,
                step INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                photo_id TEXT,
                status TEXT DEFAULT 'draft',
                channel_message_id INTEGER,
                winner_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                amount INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (auction_id) REFERENCES auctions(id)
            )
        """)
        await db.commit()


async def create_auction(admin_id, title, min_bid, step, start_time, end_time, photo_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO auctions (admin_id, title, min_bid, step, start_time, end_time, photo_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'draft')",
            (admin_id, title, min_bid, step, start_time, end_time, photo_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_auction(auction_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,))
        return await cursor.fetchone()


async def get_active_auctions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE status = 'active' AND start_time <= ? AND end_time > ?",
            (now, now)
        )
        return await cursor.fetchall()


async def get_all_auctions_by_admin(admin_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE admin_id = ? ORDER BY created_at DESC",
            (admin_id,)
        )
        return await cursor.fetchall()


async def update_auction_status(auction_id, status, channel_message_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if channel_message_id:
            await db.execute(
                "UPDATE auctions SET status = ?, channel_message_id = ? WHERE id = ?",
                (status, channel_message_id, auction_id)
            )
        else:
            await db.execute(
                "UPDATE auctions SET status = ? WHERE id = ?",
                (status, auction_id)
            )
        await db.commit()


async def set_winner(auction_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE auctions SET winner_id = ? WHERE id = ?",
            (user_id, auction_id)
        )
        await db.commit()


async def add_bid(auction_id, user_id, username, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO bids (auction_id, user_id, username, amount) VALUES (?, ?, ?, ?)",
            (auction_id, user_id, username, amount)
        )
        await db.commit()
        return cursor.lastrowid


async def get_top_bid(auction_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bids WHERE auction_id = ? ORDER BY amount DESC, created_at ASC LIMIT 1",
            (auction_id,)
        )
        return await cursor.fetchone()


async def get_bids_for_auction(auction_id, limit=None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM bids WHERE auction_id = ? ORDER BY amount DESC, created_at ASC"
        if limit:
            query += f" LIMIT {limit}"
        cursor = await db.execute(query, (auction_id,))
        return await cursor.fetchall()


async def get_user_bid(auction_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bids WHERE auction_id = ? AND user_id = ? ORDER BY amount DESC LIMIT 1",
            (auction_id, user_id)
        )
        return await cursor.fetchone()


async def check_duplicate_bid(auction_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bids WHERE auction_id = ? AND amount = ? ORDER BY created_at DESC LIMIT 1",
            (auction_id, amount)
        )
        return await cursor.fetchone()


async def get_pending_auctions():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE status = 'draft'",
        )
        return await cursor.fetchall()


async def get_auctions_to_end():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "SELECT * FROM auctions WHERE status = 'active' AND end_time <= ?",
            (now,)
        )
        return await cursor.fetchall()
