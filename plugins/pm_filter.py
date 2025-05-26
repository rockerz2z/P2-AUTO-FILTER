import asyncio
import re
from time import time as time_now
import math, os
import qrcode, random
from pyrogram.errors import ListenerTimeout
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from datetime import datetime, timedelta
from info import IS_PREMIUM, PICS, PM_SEARCH, TUTORIAL, SHORTLINK_API, SHORTLINK_URL, RECEIPT_SEND_USERNAME, UPI_ID, UPI_NAME, PRE_DAY_AMOUNT, SECOND_FILES_DATABASE_URL, ADMINS, URL, MAX_BTN, BIN_CHANNEL, IS_STREAM, DELETE_TIME, FILMS_LINK, LOG_CHANNEL, SUPPORT_GROUP, SUPPORT_LINK, UPDATES_LINK, LANGUAGES, QUALITY
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram import Client, filters, enums
from utils import is_premium, get_size, is_subscribed, is_check_admin, get_wish, get_shortlink, get_readable_time, get_poster, temp, get_settings, save_group_settings # get_settings imported from utils
from database.users_chats_db import db
from database.ia_filterdb import get_search_results,delete_files, db_count_documents, second_db_count_documents
# from plugins.commands import get_grp_stg # This line is removed

BUTTONS = {}
CAP = {}

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith("/"):
        return
    if not PM_SEARCH:
        return await message.reply_text("PM search is currently disabled.")

    verify_status = await get_verify_status(message.from_user.id)
    if IS_VERIFY and not verify_status['is_verified'] and not await is_premium(message.from_user.id, client):
        await message.reply_text(
            script.VERIFY_TXT.format(
                random.choice(PICS),
                message.from_user.mention,
                script.VERIFY_INFO_TXT,
                RECEIPT_SEND_USERNAME,
                UPI_ID,
                UPI_NAME,
                PRE_DAY_AMOUNT
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("✅ Verify Now", callback_data="verify_2")],
                    [InlineKeyboardButton("💰 Buy Premium", callback_data="buy_premium")],
                    [InlineKeyboardButton("👨‍💻 Developer", url=SUPPORT_GROUP)]
                ]
            )
        )
        return

    is_fsub = await is_subscribed(client, message)
    if is_fsub:
        buttons = []
        for btn in is_fsub:
            buttons.append(btn)
        buttons.append([InlineKeyboardButton("🔄 Try Again", callback_data="fsub_check")])
        await message.reply_text(
            script.FORCE_SUB_TEXT,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    search = message.text.lower()
    total_results = await db_count_documents(search)
    second_total_results = await second_db_count_documents(search)

    if total_results == 0 and second_total_results == 0:
        btn = [
            [InlineKeyboardButton("How to Use?", url=TUTORIAL)],
            [InlineKeyboardButton("Search on web", url=f"https://www.google.com/search?q={search}")],
            [InlineKeyboardButton("🔰 Updates Channel", url=UPDATES_LINK),
             InlineKeyboardButton("💡 Support Group", url=SUPPORT_LINK)]
        ]
        await message.reply_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search),
                                 reply_markup=InlineKeyboardMarkup(btn))
        await temp.BOT.send_message(LOG_CHANNEL, f"#No_Result\n\nRequester: {message.from_user.mention}\nContent: {search}")
        return

    s = await message.reply_text("Searching...")

    # Using get_settings from utils.py
    chat_settings = await get_settings(message.chat.id)
    pm_search_enabled = chat_settings.get("pm_search", True)

    if not pm_search_enabled:
        await s.edit_text("PM Search is currently disabled for this chat.")
        return

    offset = 0
    total_results = 0
    results = []

    # Try fetching from first database
    db_results = await get_search_results(search, offset=offset)
    results.extend(db_results)
    total_results += len(db_results)

    # If not enough results, try fetching from second database
    if len(results) < MAX_BTN and SECOND_FILES_DATABASE_URL:
        second_db_results = await get_search_results(search, offset=offset, db_type='second_db')
        results.extend(second_db_results)
        total_results += len(second_db_results)

    if not results:
        btn = [
            [InlineKeyboardButton("How to Use?", url=TUTORIAL)],
            [InlineKeyboardButton("Search on web", url=f"https://www.google.com/search?q={search}")],
            [InlineKeyboardButton("🔰 Updates Channel", url=UPDATES_LINK),
             InlineKeyboardButton("💡 Support Group", url=SUPPORT_LINK)]
        ]
        await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search),
                                 reply_markup=InlineKeyboardMarkup(btn))
        await temp.BOT.send_message(LOG_CHANNEL, f"#No_Result\n\nRequester: {message.from_user.mention}\nContent: {search}")
        return

    btn = [
        [InlineKeyboardButton("How to Use?", url=TUTORIAL)],
        [InlineKeyboardButton("Search on web", url=f"https://www.google.com/search?q={search}")],
        [InlineKeyboardButton("🔰 Updates Channel", url=UPDATES_LINK),
         InlineKeyboardButton("💡 Support Group", url=SUPPORT_LINK)]
    ]
    try:
        movies = await get_poster(search, bulk=True)
    except:
        n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return
    if not movies:
        n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await temp.BOT.send_message(LOG_CHANNEL, f"#No_Result\n\nRequester: {message.from_user.mention}\nContent: {search}")
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return
    movies = list(dict.fromkeys(movies))
    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spolling#{movie.movieID}#{user}")
    ]
        for movie in movies
    ]
    buttons.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    s = await s.edit_text(text=f"👋 Hello {message.from_user.mention},\n\nI couldn't find exact matches. Here are some related movies/series from IMDb:", reply_markup=InlineKeyboardMarkup(buttons))
