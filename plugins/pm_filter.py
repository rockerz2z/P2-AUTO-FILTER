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
from utils import is_premium, get_size, is_subscribed, is_check_admin, get_wish, get_shortlink, get_readable_time, get_poster, temp, get_settings, save_group_settings
from database.users_chats_db import db
from database.ia_filterdb import get_search_results,delete_files, db_count_documents, second_db_count_documents
from plugins.commands import get_grp_stg


BUTTONS = {}
CAP = {}

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith("/"):
        return # Ignore commands
    if not PM_SEARCH:
        return await message.reply('PM Search is disabled.')

    # Check if user is banned
    if message.from_user.id in temp.BANNED_USERS:
        buttons = [[
            InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
        ]]
        return await message.reply(f'Sorry {message.from_user.mention},\nMy owner has banned you from using me! If you want to know more, contact the support group.\nReason - <code>{await db.get_ban_status(message.from_user.id).get("ban_reason", "No reason specified.")}</code>',
                                   reply_markup=InlineKeyboardMarkup(buttons))

    # Check force subscription
    if not await is_subscribed(client, message.from_user.id):
        buttons = [[
            InlineKeyboardButton('Join Updates Channel', url=UPDATES_LINK),
            InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
        ]]
        return await message.reply_text(
            f"You need to join my updates channel and support group to proceed.\n\n{script.FORCE_SUB_TEXT}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Check verification status
    verify_status = await db.get_verify_status(message.from_user.id)
    if not verify_status.get('is_verified') and not await is_premium(message.from_user.id, client):
        buttons = [[
            InlineKeyboardButton('Verify Now', callback_data='verify_user#pm_search')
        ]]
        return await message.reply_text(
            f"You need to verify yourself to search for files.\n\n{script.VERIFY_TXT}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Add user to database if not already present
    if not await db.get_user(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)

    search = message.text
    s = await message.reply_text("Searching...")
    query = search.replace(" ", "%").strip()
    files = await get_search_results(query, file_type=None, offset=0, filter=True)

    if not files:
        btn = [[
            InlineKeyboardButton('➕ Request', url=f"https://t.me/{(await client.get_chat(SUPPORT_GROUP)).username}")
        ]]
        if FILMS_LINK:
            btn.append([InlineKeyboardButton("🎞️ Films", url=FILMS_LINK)])
        
        # Use random photo if PICS is available, otherwise just send text
        if PICS:
            try:
                n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
                # Fallback to text if photo fails
            except Exception as e:
                print(f"Error sending photo in pm_search: {e}")
                n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        else:
            n = await s.edit_text(text=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))

        await temp.BOT.send_message(LOG_CHANNEL, f"#No_Result\n\nRequester: {message.from_user.mention}\nContent: {search}")
        await asyncio.sleep(60) # Keep message for 60 seconds
        try:
            await n.delete()
            await message.delete() # Delete user's message after response
        except Exception as e:
            print(f"Error deleting message after no result: {e}")
        return

    temp.FILES[f"{message.from_user.id}-{s.id}"] = files[:MAX_BTN] # Store only the first MAX_BTN files
    buttons = []
    for file in files[:MAX_BTN]:
        buttons.append([InlineKeyboardButton(text=f"{file.get('file_name', 'N/A')}", callback_data=f"file_X#{file['_id']}")])
    
    if len(files) > MAX_BTN:
        buttons.append([InlineKeyboardButton("Next", callback_data=f"file_next#{MAX_BTN}")])
    
    buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data="close_data")])

    await s.edit_text(
        text=script.FILE_TXT.format(query=search, count=len(files), user=message.from_user.mention, wish=get_wish()),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )
    temp.DELETE_MSG_IDS[message.from_user.id] = [s.id, message.id] # Store message IDs for later deletion


@Client.on_message(filters.private & filters.media & filters.incoming)
async def media_filter(client, message):
    if IS_STREAM:
        # This section is for logging or further processing if streaming is enabled
        # It doesn't perform filtering or sending itself in PM
        print(f"Received media in PM from {message.from_user.id}. Stream is enabled.")
    # No other processing for media in PM is currently defined in this filter.
    # If the intent was to filter media sent *to* the bot, more logic would be needed here.


@Client.on_callback_query(filters.regex(r'^file_X'))
async def get_file(bot, query):
    _, file_id = query.data.split("#")
    try:
        msg = await bot.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=FILE_CAPTION.format(file_name=query.message.reply_to_message.text) if FILE_CAPTION else None
        )
        if PM_FILE_DELETE_TIME:
            await asyncio.sleep(PM_FILE_DELETE_TIME)
            await msg.delete()
    except Exception as e:
        await query.answer(f"Error sending file: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^file_next"))
async def file_next(bot, query):
    ident, offset = query.data.split("#")
    offset = int(offset)
    user_id = query.from_user.id
    msg_id = query.message.id

    if f"{user_id}-{msg_id}" not in BUTTONS:
        BUTTONS[f"{user_id}-{msg_id}"] = temp.FILES.get(f"{user_id}-{query.message.reply_to_message.id}", [])
        CAP[f"{user_id}-{msg_id}"] = query.message.reply_to_message.text

    files = BUTTONS[f"{user_id}-{msg_id}"]
    
    if not files:
        await query.answer("No more files found for this query.", show_alert=True)
        return

    buttons = []
    current_files = files[offset:offset + MAX_BTN]
    for file in current_files:
        buttons.append([InlineKeyboardButton(text=f"{file.get('file_name', 'N/A')}", callback_data=f"file_X#{file['_id']}")])

    if len(files) > offset + MAX_BTN:
        buttons.append([InlineKeyboardButton("Next", callback_data=f"file_next#{offset + MAX_BTN}")])
    if offset - MAX_BTN >= 0:
        buttons.append([InlineKeyboardButton("Back", callback_data=f"file_next#{offset - MAX_BTN}")])

    buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data="close_data")])
    
    try:
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.answer(f"Error updating message: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^short_lk"))
async def short_lk(bot, query):
    ident, file_id = query.data.split("#")
    file_details = await get_file_details(file_id)
    if not file_details:
        return await query.answer("File not found!", show_alert=True)
    
    # Check force subscription again for shortlink access
    if not await is_subscribed(bot, query.from_user.id):
        buttons = [[
            InlineKeyboardButton('Join Updates Channel', url=UPDATES_LINK),
            InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
        ]]
        return await query.message.edit_text(
            f"You need to join my updates channel and support group to get the shortlink.\n\n{script.FORCE_SUB_TEXT}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # Check verification status again for shortlink access
    verify_status = await db.get_verify_status(query.from_user.id)
    if not verify_status.get('is_verified') and not await is_premium(query.from_user.id, bot):
        buttons = [[
            InlineKeyboardButton('Verify Now', callback_data='verify_user#shortlink_verify')
        ]]
        return await query.message.edit_text(
            f"You need to verify yourself to get the shortlink.\n\n{script.VERIFY_TXT}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    short_link = await get_shortlink(file_details['file_name'], file_details['_id'])
    if not short_link:
        return await query.answer("Failed to generate shortlink.", show_alert=True)
    
    buttons = [[
        InlineKeyboardButton("🔗 Get Link", url=short_link)
    ]]
    await query.answer("Shortlink generated!", show_alert=True)
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^short_lk_next"))
async def short_lk_next(bot, query):
    ident, offset = query.data.split("#")
    offset = int(offset)
    user_id = query.from_user.id
    msg_id = query.message.id

    if f"{user_id}-{msg_id}-short" not in BUTTONS:
        return await query.answer("Session expired or no files found.", show_alert=True)

    files = BUTTONS[f"{user_id}-{msg_id}-short"]
    
    if not files:
        await query.answer("No more files for shortlink generation.", show_alert=True)
        return

    buttons = []
    current_files = files[offset:offset + MAX_BTN]
    for file in current_files:
        buttons.append([InlineKeyboardButton(text=f"{file.get('file_name', 'N/A')}", callback_data=f"short_lk#{file['_id']}")])

    if len(files) > offset + MAX_BTN:
        buttons.append([InlineKeyboardButton("Next", callback_data=f"short_lk_next#{offset + MAX_BTN}")])
    if offset - MAX_BTN >= 0:
        buttons.append([InlineKeyboardButton("Back", callback_data=f"short_lk_next#{offset - MAX_BTN}")])

    buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data="close_data")])
    
    try:
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await query.answer(f"Error updating message: {e}", show_alert=True)


@Client.on_callback_query(filters.regex(r"^spolling"))
async def spolling_search(bot, query):
    _, movie_id, user = query.data.split("#")
    user = int(user)
    if not user == query.from_user.id:
        return await query.answer("This search was initiated by another user.", show_alert=True)
    
    await query.answer("Getting movie details...")
    s = await query.message.edit_text("Fetching movie details...")
    
    try:
        movie = await get_poster(query=movie_id, bulk=False)
        if not movie:
            return await s.edit_text("Could not find movie details.")
        
        text = script.IMDB_TEMPLATE.format(
            query=movie_id,
            title=movie.get('title'),
            votes=movie.get('votes'),
            aka=movie.get('aka'),
            seasons=movie.get('seasons'),
            box_office=movie.get('box_office'),
            cast=movie.get('cast'),
            release_date=movie.get('release_date'),
            runtime=movie.get('runtime'),
            genres=movie.get('genres'),
            production=movie.get('production'),
            companies=movie.get('companies'),
            countries=movie.get('countries'),
            languages=movie.get('languages'),
            directors=movie.get('directors'),
            writers=movie.get('writers'),
            plot=movie.get('plot'),
            top_cast=movie.get('top_cast'),
            poster=movie.get('poster'),
            imdb_id=movie.get('imdb_id'),
            imdb_url=movie.get('imdb_url'),
            tomatoes=movie.get('tomatoes'),
            crtcs=movie.get('crtcs'),
            rated=movie.get('rated'),
            budget=movie.get('budget'),
            collections=movie.get('collections')
        )
        
        buttons = [[
            InlineKeyboardButton('Search Again', switch_inline_query_current_chat=movie.get('title'))
        ]]
        
        if movie.get('poster'):
            try:
                await s.delete()
                await bot.send_photo(
                    chat_id=query.message.chat.id,
                    photo=movie.get('poster'),
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                await s.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=False)
            except Exception as e:
                print(f"Error sending IMDb poster: {e}")
                await s.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=False)
        else:
            await s.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=False)
    except Exception as e:
        await s.edit_text(f"An error occurred while fetching movie details: {e}")


@Client.on_callback_query(filters.regex(r"^get_movie_idx"))
async def get_movie_idx(bot, query):
    _, query_string, offset = query.data.split("#")
    offset = int(offset)
    
    if not query_string:
        return await query.answer("Invalid query string.", show_alert=True)

    s = await query.message.edit_text("Searching for files related to the movie...")
    
    # Assuming get_search_results can handle movie titles as query
    files = await get_search_results(query_string, file_type=None, offset=offset, filter=True)

    if not files:
        await s.edit_text("No files found for this movie.")
        await asyncio.sleep(60)
        try:
            await s.delete()
            await query.message.delete()
        except:
            pass
        return

    buttons = []
    for file in files[:MAX_BTN]:
        buttons.append([InlineKeyboardButton(text=f"{file.get('file_name', 'N/A')}", callback_data=f"file_X#{file['_id']}")])
    
    if len(files) > MAX_BTN:
        buttons.append([InlineKeyboardButton("Next", callback_data=f"get_movie_idx#{query_string}#{offset + MAX_BTN}")])
    
    buttons.append([InlineKeyboardButton("🚫 Close 🚫", callback_data="close_data")])

    await s.edit_text(
        text=script.FILE_TXT.format(query=query_string, count=len(files), user=query.from_user.mention, wish=get_wish()),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )
    temp.DELETE_MSG_IDS[query.from_user.id] = [s.id, query.message.id] # Store message IDs for later deletion


@Client.on_callback_query(filters.regex(r'^close_data'))
async def close_data(bot, query):
    try:
        await query.message.delete()
        if query.from_user.id in temp.DELETE_MSG_IDS:
            for msg_id in temp.DELETE_MSG_IDS[query.from_user.id]:
                try:
                    await bot.delete_messages(chat_id=query.from_user.id, message_ids=msg_id)
                except Exception as e:
                    print(f"Error deleting message {msg_id}: {e}")
            del temp.DELETE_MSG_IDS[query.from_user.id]
        if f"{query.from_user.id}-{query.message.id}" in BUTTONS:
            del BUTTONS[f"{query.from_user.id}-{query.message.id}"]
        if f"{query.from_user.id}-{query.message.id}" in CAP:
            del CAP[f"{query.from_user.id}-{query.message.id}"]
    except Exception as e:
        await query.answer(f"Error closing message: {e}", show_alert=True)
