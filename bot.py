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
from pyrogram import types
from pyrogram import Client
from pyrogram.errors import FloodWait
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
from web import web_app
from info import INDEX_CHANNELS, SUPPORT_GROUP, LOG_CHANNEL, API_ID, DATA_DATABASE_URL, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, SECOND_FILES_DATABASE_URL, FILES_DATABASE_URL
from utils import temp, get_readable_time, check_premium
from database.users_chats_db import db
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

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
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        temp.ME = await self.get_me()
        temp.U_NAME = temp.ME.username
        temp.B_NAME = temp.ME.first_name
        
        # Connect to MongoDB databases
        # Main Database
        try:
            temp.BOT = self
            db_client = MongoClient(DATA_DATABASE_URL, server_api=ServerApi('1'))
            await db_client.admin.command('ping')
            logger.info("MongoDB Data DB Connected!")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Data DB: {e}", exc_info=True)
            exit() # Exit if main DB connection fails

        # Files Database 1
        try:
            files_db_client = MongoClient(FILES_DATABASE_URL, server_api=ServerApi('1'))
            await files_db_client.admin.command('ping')
            logger.info("MongoDB Files DB 1 Connected!")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB Files DB 1: {e}", exc_info=True)
            # This is not critical to exit, but log it

        # Files Database 2 (Optional)
        if SECOND_FILES_DATABASE_URL:
            try:
                second_files_db_client = MongoClient(SECOND_FILES_DATABASE_URL, server_api=ServerApi('1'))
                await second_files_db_client.admin.command('ping')
                logger.info("MongoDB Files DB 2 Connected!")
            except Exception as e:
                logger.warning(f"Failed to connect to MongoDB Files DB 2: {e}. Proceeding without it.", exc_info=True)
        
        # Start web server
        try:
            # Check if web_app is an Application instance
            if isinstance(web_app, web.Application):
                runner = web.AppRunner(web_app)
                await runner.setup()
                site = web.TCPSite(runner, '0.0.0.0', PORT)
                await site.start()
                logger.info(f"Web server started on port {PORT}")
            else:
                logger.error("web_app is not an aiohttp.web.Application instance. Web server will not start.")
        except Exception as e:
            logger.error(f"Error starting web server: {e}", exc_info=True)

        # Start premium check task
        asyncio.create_task(check_premium(self))

        logger.info(f"@{temp.U_NAME} is started now ✓")

        # Send startup message to log channel
        if LOG_CHANNEL:
            try:
                await self.send_message(LOG_CHANNEL, f"#Restart\n\n**{temp.ME.mention} Is Restarted ✅**")
            except Exception as e:
                logger.error(f"Failed to send startup message to LOG_CHANNEL: {e}", exc_info=True)

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot Stopped.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0
    ) -> AsyncGenerator["types.Message", None]:
        """
        Iterate through a chat's messages.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                async for message in app.iter_messages("HA_Bots", 1000, 100):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()
