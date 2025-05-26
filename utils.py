import logging
from datetime import datetime, timedelta
from pyrogram.errors import UserNotParticipant, FloodWait
from info import LONG_IMDB_DESCRIPTION, ADMINS, IS_PREMIUM
from imdb import Cinemagoer
import asyncio
from pyrogram.types import InlineKeyboardButton
from pyrogram import enums
import re
from database.users_chats_db import db
from shortzy import Shortzy
import requests
import aiohttp
import aiofiles
import os

logger = logging.getLogger(__name__)

imdb = Cinemagoer()

class temp(object):
    START_TIME = 0
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CANCEL = False
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    VERIFICATIONS = {}
    FILES = {}
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}

async def is_subscribed(bot, query):
    btn = []
    if await is_premium(query.from_user.id, bot):
        return btn
    stg = db.get_bot_sttgs()
    if not stg or not stg.get('FORCE_SUB_CHANNELS'):
        return btn
    for id in stg.get('FORCE_SUB_CHANNELS').split(' '):
        chat = await bot.get_chat(int(id))
        try:
            await bot.get_chat_member(int(id), query.from_user.id)
        except UserNotParticipant:
            btn.append(
                [InlineKeyboardButton(f'Join : {chat.title}', url=chat.invite_link)]
            )
    if stg and stg.get('REQUEST_FORCE_SUB_CHANNELS'):
        chat = await bot.get_chat(int(stg.get('REQUEST_FORCE_SUB_CHANNELS')))
        if not await db.find_join_req(query.from_user.id, chat.id):
            btn.append(
                [InlineKeyboardButton(f'Request to Join : {chat.title}', url=chat.invite_link)]
            )
    return btn

async def is_premium(user_id, client):
    """
    Checks if a user is premium.
    This function should retrieve premium status from your database.
    """
    if user_id in ADMINS:
        return True # Admins are always considered premium

    user_data = await db.get_user(user_id)
    if user_data and user_data.get('status', {}).get('premium'):
        premium_info = user_data.get('status', {})
        expiry_date = premium_info.get('expire')
        if expiry_date and datetime.now() < expiry_date:
            return True
        else:
            # Premium expired, update status in DB
            await db.update_premium_status(user_id, False, None)
            logger.info(f"Premium expired for user {user_id}")
            return False
    return False

async def check_premium(client):
    """
    Periodically checks premium status of users.
    """
    while True:
        logger.info("Running premium check task...")

        try:
            premium_users = await db.get_premium_users()
            for user_data in premium_users:
                user_id = user_data['id']
                premium_info = user_data.get('status', {})
                if premium_info.get('premium'):
                    expiry_date = premium_info.get('expire')
                    if expiry_date and datetime.now() > expiry_date:
                        await db.update_premium_status(user_id, False, None)
                        logger.info(f"Premium expired for user {user_id}")
                        try:
                            await client.send_message(user_id, "Your premium plan has expired!")
                        except Exception as e:
                            logger.warning(f"Could not notify user {user_id} about premium expiry: {e}")
        except Exception as e:
            logger.error(f"Error during premium check: {e}", exc_info=True)

        await asyncio.sleep(6 * 3600)

async def get_poster(query, bulk=False, id=False):
    if bulk:
        search = imdb.search_movie(query)
        if not search:
            return None
        return search
    elif id:
        search = imdb.get_movie(query)
        return search
    else:
        search = imdb.search_movie(query)
        if not search:
            return None
        return search[0]

def get_size(size):
    """Get size in readable format"""
    if size < 1000:
        return f"{size} B"
    siz = '{:.2f}'.format(size / 1024)
    if float(siz) < 1000:
        return f"{siz} KB"
    siz = '{:.2f}'.format(size / (1024 * 1024))
    if float(siz) < 1000:
        return f"{siz} MB"
    siz = '{:.2f}'.format(size / (1024 * 1024 * 1024))
    if float(siz) < 1000:
        return f"{siz} GB"

async def is_check_admin(client, chat_id, id):
    try:
        member = await client.get_chat_member(chat_id, id)
    except UserNotParticipant:
        return False
    if member.status in [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
        return True
    return False

async def upload_image(filepath):
    """
    Uploads an image to uguu.se and returns the direct link.
    """
    UGUU_URL = "https://uguu.se/upload.php"

    async with aiohttp.ClientSession() as session:
        async with aiofiles.open(filepath, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('files[]', await f.read(), filename=os.path.basename(filepath), content_type='application/octet-stream')

            try:
                async with session.post(UGUU_URL, data=data) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        match = re.search(r'(https?://\S+\.\S+)', response_text)
                        if match:
                            return match.group(0)
                        else:
                            logger.error(f"Uguu.se upload successful but no direct link found in response: {response_text}")
                            return None
                    else:
                        logger.error(f"Uguu.se upload failed with status {response.status}: {await response.text()}")
                        return None
            except aiohttp.ClientError as e:
                logger.error(f"Network error during uguu.se upload: {e}", exc_info=True)
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred during uguu.se upload: {e}", exc_info=True)
                return None

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.error(f"Error removing local file {filepath}: {e}")

# This function was missing `async` keyword
async def get_shortlink(url, api, link): # Changed to async def
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link

def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result

def get_wish():
    time = datetime.now()
    now = time.strftime("%H")
    if now < "12":
        status = "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞"
    elif now < "18":
        status = "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗"
    else:
        status = "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"
    return status

async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:]
        if value:
            value = int(value)
        return value, unit

    time_string = time_string.lower().strip()
    if not time_string:
        return 0

    value, unit = extract_value_and_unit(time_string)

    if not value or not unit:
        raise ValueError("Invalid time string format")

    if unit.startswith('s'):
        return value
    elif unit.startswith('m'):
        return value * 60
    elif unit.startswith('h'):
        return value * 3600
    elif unit.startswith('d'):
        return value * 86400
    else:
        raise ValueError("Invalid time unit. Use s (seconds), m (minutes), h (hours), d (days).")

async def get_verify_status(user_id):
    user = temp.VERIFICATIONS.get(user_id)
    if not user:
        return {'is_verified': False}

    current_time = datetime.now()
    last_verified = user['last_verified']

    if current_time - last_verified <= timedelta(days=1):
        return {'is_verified': True, 'remaining_time': (last_verified + timedelta(days=1)) - current_time}
    else:
        temp.VERIFICATIONS.pop(user_id, None)
        return {'is_verified': False}

async def update_verify_status(user_id):
    temp.VERIFICATIONS[user_id] = {'is_verified': True, 'last_verified': datetime.now()}

async def get_settings(chat_id):
    chat_settings = temp.SETTINGS.get(chat_id)
    if not chat_settings:
        chat_settings = await db.get_chat(chat_id)
        if not chat_settings:
            temp.SETTINGS[chat_id] = {
                'file_caption': None,
                'pm_search': True,
                'tutorial': None,
                'max_btn': 5
            }
        else:
            temp.SETTINGS[chat_id] = chat_settings.get('settings', {})
    return temp.SETTINGS[chat_id]

async def save_group_settings(chat_id, key, value):
    stg = await get_settings(chat_id)
    stg[key] = value
    temp.SETTINGS[chat_id] = stg
    await db.update_chat_sttgs(chat_id, stg)
    return stg

async def is_check_admin_in_db(user_id):
    return False
