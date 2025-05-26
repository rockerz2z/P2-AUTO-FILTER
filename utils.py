import logging
from pyrogram.errors import UserNotParticipant, FloodWait, RPCError
from info import LONG_IMDB_DESCRIPTION, ADMINS, IS_PREMIUM, LOG_CHANNEL # Added LOG_CHANNEL
from imdb import Cinemagoer
import asyncio
from pyrogram.types import InlineKeyboardButton
from pyrogram import enums
import re
from datetime import datetime, timedelta
from database.users_chats_db import db # Ensure this is an async db object
from shortzy import Shortzy
import requests # Still used for get_poster, consider replacing with aiohttp if possible

logger = logging.getLogger(__name__) # Initialize logger

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
    VERIFICATIONS = {} # Stores verification data temporarily
    FILES = {} # Stores temporary file lists for pagination
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    BOT = None
    PREMIUM = {}
    DELETE_MSG_IDS = {} # To store message IDs for auto-deletion

async def is_subscribed(bot, user_id):
    """Checks if a user is subscribed to force subscribe channels."""
    btn = []
    # Check if user is premium, if so, no force sub needed
    is_prem = await is_premium(user_id, bot)
    if is_prem:
        return True # Premium users bypass force sub

    stg = await db.get_bot_sttgs() # Await db call
    force_sub_channels_str = stg.get('FORCE_SUB_CHANNELS')

    if not force_sub_channels_str:
        return True # No force sub channels configured

    for id_str in force_sub_channels_str.split(' '):
        try:
            chat_id = int(id_str)
            chat = await bot.get_chat(chat_id)
            try:
                member = await bot.get_chat_member(chat_id, user_id)
                if member.status in ["member", "administrator", "creator"]:
                    continue # User is subscribed
                else:
                    # User is restricted, left, or kicked
                    btn.append(
                        [InlineKeyboardButton(f'Join : {chat.title}', url=chat.invite_link)]
                    )
            except UserNotParticipant:
                btn.append(
                    [InlineKeyboardButton(f'Join : {chat.title}', url=chat.invite_link)]
                )
            except Exception as e:
                logger.error(f"Error checking chat member for {user_id} in {chat_id}: {e}")
                # If there's an error getting chat member, assume not subscribed for safety
                btn.append(
                    [InlineKeyboardButton(f'Join : {chat.title}', url=chat.invite_link)]
                )
        except ValueError:
            logger.warning(f"Invalid channel ID in FORCE_SUB_CHANNELS: {id_str}")
            continue # Skip invalid channel IDs
        except Exception as e:
            logger.error(f"Error getting chat info for force sub channel {id_str}: {e}")
            continue # Skip if chat info cannot be retrieved

    if btn:
        return btn # Return buttons if not subscribed to all
    return True # All checks passed, user is subscribed


async def is_premium(user_id, bot):
    """Checks if a user is premium."""
    try:
        plan = await db.get_plan(user_id) # Await db call
        if plan and plan.get('premium'):
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        return False

async def upload_image(url):
    """Uploads an image from a URL (placeholder, actual upload needs Pyrogram's send_photo)."""
    # This function seems to be a placeholder from a web context.
    # In a Pyrogram bot, you would download the image and then use bot.send_photo.
    # For now, keeping it as is, but note it might not directly upload to Telegram.
    return url

async def get_settings(chat_id):
    """Fetches chat settings."""
    return await db.get_settings(chat_id) # Await db call

async def save_group_settings(chat_id, settings):
    """Saves group settings."""
    await db.update_settings(chat_id, settings) # Await db call


def get_size(size):
    """Converts bytes to human-readable size."""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EBs"]
    if size == 0:
        return "0 Byte"
    i = int(math.log(size, 1024))
    return f"{round(size / (1024 ** i), 2)} {units[i]}"

async def is_check_admin(client, chat_id, user_id):
    """Checks if a user is an admin in a chat."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        return False

async def is_check_admin_in_db(client, chat_id, user_id):
    """Checks if a user is an admin in a chat and also in the bot's ADMINS list."""
    if user_id in ADMINS:
        return True
    return await is_check_admin(client, chat_id, user_id)


async def get_shortlink(file_name, file_id):
    """Generates a shortlink for a file."""
    stg = await db.get_bot_sttgs() # Await db call
    url = stg.get('SHORTLINK_URL')
    api = stg.get('SHORTLINK_API')
    
    if not url or not api:
        logger.warning("Shortlink URL or API key is not configured.")
        return None

    try:
        shortzy = Shortzy(api_key=api, base_site=url)
        # Assuming the 'link' to be shortened is a direct download link or unique identifier
        # For a bot, this might be a link to your web server's download endpoint
        # Example: f"{URL}download/{file_id}" if URL is your web server base URL
        # For simplicity, let's assume it's just the file_id for now, and the shortener knows how to handle it.
        link_to_shorten = f"{url}download/{file_id}" # Assuming URL is your web server base
        short_link = await shortzy.convert(link_to_shorten)
        return short_link
    except Exception as e:
        logger.error(f"Error generating shortlink for {file_name} ({file_id}): {e}")
        return None

def get_readable_time(seconds):
    """Converts seconds to human-readable time."""
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name}'
    return result if result else "0s" # Ensure '0s' for 0 seconds

def get_wish():
    """Returns a greeting based on the current time."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "ɢᴏᴏᴅ ᴍᴏʀɴɪɴɢ 🌞"
    elif 12 <= current_hour < 18:
        return "ɢᴏᴏᴅ ᴀꜰᴛᴇʀɴᴏᴏɴ 🌗"
    else:
        return "ɢᴏᴏᴅ ᴇᴠᴇɴɪɴɢ 🌘"
    
async def get_seconds(time_string):
    """Converts a time string (e.g., '1h', '30m', '5d') to seconds."""
    def extract_value_and_unit(ts):
        value = ""
        unit = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:].lower()
        if value:
            value = int(value)
        return value, unit

    value, unit = extract_value_and_unit(time_string)
    
    if not value or not unit:
        raise ValueError("Invalid time string format. Expected format like '1h', '30m', '5d'.")

    if unit == 's':
        return value
    elif unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        raise ValueError(f"Unknown time unit: {unit}. Supported units: s, m, h, d.")

async def get_poster(query, bulk=False):
    """Fetches movie poster and details from IMDb."""
    try:
        if bulk: # For multiple results
            movies = imdb.search_movie(query)
            if not movies:
                return []
            return movies[:10] # Return top 10 results
        else: # For single result
            movie = imdb.search_movie(query)
            if not movie:
                return None
            movie_id = movie[0].movieID
            full_movie = imdb.get_movie(movie_id)
            if not full_movie:
                return None

            # Extract relevant details
            title = full_movie.get('title')
            year = full_movie.get('year')
            plot = full_movie.get('plot outline')
            poster = full_movie.get('full-size poster')
            rating = full_movie.get('rating')
            genres = ', '.join(full_movie.get('genres', []))
            directors = ', '.join([d['name'] for d in full_movie.get('directors', [])])
            cast = ', '.join([c['name'] for c in full_movie.get('cast', [])[:5]]) # Top 5 cast

            return {
                'title': title,
                'year': year,
                'plot': plot,
                'poster': poster,
                'rating': rating,
                'genres': genres,
                'directors': directors,
                'cast': cast,
                'imdb_url': f"https://www.imdb.com/title/tt{movie_id}/",
                'movieID': movie_id,
                # Add other fields if needed for your template
            }
    except Exception as e:
        logger.error(f"Error fetching IMDb poster for query '{query}': {e}")
        return None

async def get_verify_status(user_id):
    """Gets user verification status from DB."""
    return await db.get_verify_status(user_id) # Await db call

async def update_verify_status(user_id, status_data):
    """Updates user verification status in DB."""
    await db.update_verify_status(user_id, status_data) # Await db call


async def broadcast_messages(user_id, message, pin=False):
    """Sends a message to a user for broadcast."""
    try:
        if pin:
            await message.copy(chat_id=user_id, disable_notification=False).pin(disable_notification=True)
        else:
            await message.copy(chat_id=user_id, disable_notification=False)
        return 'Success'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message, pin) # Retry after flood wait
    except RPCError as e:
        logger.error(f"RPCError during broadcast to {user_id}: {e}")
        # Handle specific RPC errors like UserBlocked, UserDeactivated etc.
        # For example, if user blocked bot, you might want to remove them from DB.
        if "USER_BOT_BLOCKED" in str(e) or "USER_DEACTIVATED" in str(e):
            await db.delete_user(user_id) # Example: delete user if blocked/deactivated
        return 'Error'
    except Exception as e:
        logger.error(f"Unexpected error during broadcast to {user_id}: {e}", exc_info=True)
        return 'Error'

async def groups_broadcast_messages(chat_id, message, pin=False):
    """Sends a message to a group for broadcast."""
    try:
        if pin:
            await message.copy(chat_id=chat_id, disable_notification=False).pin(disable_notification=True)
        else:
            await message.copy(chat_id=chat_id, disable_notification=False)
        return 'Success'
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast_messages(chat_id, message, pin) # Retry after flood wait
    except RPCError as e:
        logger.error(f"RPCError during group broadcast to {chat_id}: {e}")
        # Handle specific RPC errors like ChatWriteForbidden, ChatRestricted etc.
        # For example, if bot is kicked from chat, you might want to remove chat from DB.
        if "CHAT_WRITE_FORBIDDEN" in str(e) or "CHAT_KICKED" in str(e):
            await db.delete_chat(chat_id) # Example: delete chat if bot is kicked
        return 'Error'
    except Exception as e:
        logger.error(f"Unexpected error during group broadcast to {chat_id}: {e}", exc_info=True)
        return 'Error'
