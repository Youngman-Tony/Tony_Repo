import os
from datetime import timedelta, timezone

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")
DB_PATH = os.getenv("DB_PATH", "auction.db")

MSK = timezone(timedelta(hours=3))