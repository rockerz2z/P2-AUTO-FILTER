import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('pyrogram').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

import os
import time
import asyncio
import uvloop
from pyrogram import Client
from aiohttp import web

from info import (
    INDEX_CHANNELS, SUPPORT_GROUP, LOG_CHANNEL, API_ID, DATA_DATABASE_URL,
    API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS,
    SECOND_FILES_DATABASE_URL, FILES_DATABASE_URL
)
from utils import temp
from database.users_chats_db import db
from web import web_app

uvloop.install()

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        await super().start()
        temp.START_TIME = time.time()

        # Load banned users/chats
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        # Restart confirmation message (if any)
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text='✅ Restarted Successfully!'
                )
            except Exception as e:
                logger.warning(f"Restart message failed: {e}")
            os.remove('restart.txt')

        # Store bot info globally
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        logger.info(f"Bot started as {me.first_name} (@{me.username})")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped.")


# Entry point
if __name__ == "__main__":
    bot = Bot()

    async def main():
        await bot.start()
        runner = web.AppRunner(web_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"Web server running on port {PORT}")
        await idle()

    from pyrogram import idle
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        asyncio.run(bot.stop())
