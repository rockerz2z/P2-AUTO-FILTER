import logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
# Corrected logger name from 'hydrogram' to 'pyrogram'
logging.getLogger('pyrogram').setLevel(logging.ERROR) 
logger = logging.getLogger(__name__)

import os
import time
import asyncio
import uvloop
from pyrogram import types
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError # Imported RPCError for broader error handling
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
from web import web_app # Assuming web_app is an aiohttp.web.Application instance
from info import INDEX_CHANNELS, SUPPORT_GROUP, LOG_CHANNEL, API_ID, DATA_DATABASE_URL, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, SECOND_FILES_DATABASE_URL, FILES_DATABASE_URL
from utils import temp, get_readable_time, check_premium
from database.users_chats_db import db # Assuming 'db' is an asynchronous database client
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
        
        try:
            # Fetch banned users and chats from the database
            b_users, b_chats = await db.get_banned()
            temp.BANNED_USERS = b_users
            temp.BANNED_CHATS = b_chats
        except Exception as e:
            logger.error(f"Error fetching banned users/chats from DB: {e}", exc_info=True)
            # Initialize as empty lists to prevent further errors if DB fetch fails
            temp.BANNED_USERS = []
            temp.BANNED_CHATS = []

        if os.path.exists('restart.txt'):
            try:
                with open("restart.txt") as file:
                    chat_id, msg_id = map(int, file.read().strip().split(',')) # Ensure correct parsing for comma-separated
                try:
                    # Attempt to edit the restart message
                    await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
                except RPCError as e:
                    logger.warning(f"Could not edit restart message (chat_id: {chat_id}, msg_id: {msg_id}): {e}")
                except Exception as e:
                    logger.error(f"Unexpected error while editing restart message: {e}", exc_info=True)
                finally:
                    os.remove('restart.txt') # Always try to remove the file
            except ValueError:
                logger.error("restart.txt contains invalid data. Expected 'chat_id,msg_id'. Removing file.", exc_info=True)
                os.remove('restart.txt')
            except FileNotFoundError:
                # This case is handled by os.path.exists, but good to have for robustness
                logger.info("restart.txt not found (already handled or deleted).")
            except Exception as e:
                logger.error(f"Unhandled error during restart.txt processing: {e}", exc_info=True)
                if os.path.exists('restart.txt'):
                    os.remove('restart.txt')


        temp.BOT = self # Store the bot instance in temp for global access
        try:
            me = await self.get_me() # Get bot's own information
            temp.ME = me.id
            temp.U_NAME = me.username
            temp.B_NAME = me.first_name
        except RPCError as e:
            logger.error(f"Failed to get bot's own information: {e}. Exiting.", exc_info=True)
            exit()
        except Exception as e:
            logger.error(f"Unexpected error while getting bot's info: {e}. Exiting.", exc_info=True)
            exit()
            
        try:
            # Setup and start the aiohttp web server
            app_runner = web.AppRunner(web_app)
            await app_runner.setup()
            await web.TCPSite(app_runner, "0.0.0.0", PORT).start()
            logger.info(f"Web server started on port {PORT}")
        except Exception as e:
            logger.error(f"Failed to start web server on port {PORT}: {e}. Web functionalities might be unavailable.", exc_info=True)

        # Create a background task for checking premium status
        asyncio.create_task(check_premium(self)) 

        try:
            # Send a restart notification to the log channel
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except RPCError as e:
            logger.error(f"Failed to send restart message to LOG_CHANNEL ({LOG_CHANNEL}): {e}. Make sure bot is admin there. Exiting now.", exc_info=True)
            exit()
        except Exception as e:
            logger.error(f"Unexpected error sending restart message to LOG_CHANNEL: {e}. Exiting now.", exc_info=True)
            exit()

        logger.info(f"@{temp.U_NAME} is started now ✓")

    async def stop(self, *args):
        # Gracefully stop the Pyrogram client
        await super().stop()
        logger.info("Bot Stopped! Bye...")

    async def iter_messages(self: Client, chat_id: Union[int, str], limit: int, offset: int = 0) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Maximum number of messages to return.
                
            offset (``int``, *optional*):
                Offset from which to start iterating.
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
            # Calculate how many messages to fetch in the current batch (max 200)
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return # No more messages to fetch

            # Fetch messages by ID. Pyrogram's get_messages accepts a list of IDs.
            # Note: This custom iter_messages fetches messages by a range of IDs,
            # which might not be continuous if messages were deleted.
            # Pyrogram's built-in client.iter_messages() is usually preferred for
            # iterating over a chat's history as it handles pagination and continuity better.
            try:
                messages = await self.get_messages(chat_id, list(range(current, current + new_diff + 1)))
            except FloodWait as e:
                logger.warning(f"FloodWait of {e.value} seconds encountered during iter_messages. Sleeping...")
                await asyncio.sleep(e.value)
                continue # Retry fetching the same batch
            except RPCError as e:
                logger.error(f"RPCError during iter_messages for chat {chat_id}: {e}", exc_info=True)
                break # Stop iteration on critical error
            except Exception as e:
                logger.error(f"Unexpected error during iter_messages for chat {chat_id}: {e}", exc_info=True)
                break # Stop iteration on unexpected error

            if not messages:
                break # No messages returned, end iteration

            for message in messages:
                if message: # Ensure message object is not None (can happen if some IDs don't exist)
                    yield message
                current += 1 # Increment current for the next batch

app = Bot()
app.run()
