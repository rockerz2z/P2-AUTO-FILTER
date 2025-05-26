from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultCachedDocument, InlineQuery
from database.ia_filterdb import get_search_results
from utils import get_size, temp, get_verify_status, is_subscribed, is_premium
from info import CACHE_TIME, SUPPORT_LINK, UPDATES_LINK, FILE_CAPTION, IS_VERIFY, MAX_BTN

cache_time = CACHE_TIME

def is_banned(query: InlineQuery):
    return query.from_user and query.from_user.id in temp.BANNED_USERS

@Client.on_inline_query()
async def inline_search(bot, query):
    """Show search results for given inline query"""

    if is_banned(query):
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text="You're banned user. Contact support group.",
                           switch_pm_parameter="start") # Changed parameter to 'start' for consistency
        return

    is_fsub = await is_subscribed(bot, query)
    if is_fsub is not True: # Check if it's not True (False or any error)
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text="Join my Updates Channel :(",
                           switch_pm_parameter="inline_fsub")
        return

    if IS_VERIFY: # Only check verification if IS_VERIFY is True
        verify_status = await get_verify_status(query.from_user.id)
        if not verify_status.get('is_verified') and not await is_premium(query.from_user.id, bot): # Use .get() for safety
            await query.answer(results=[],
                               cache_time=0,
                               switch_pm_text="You're not verified today :(",
                               switch_pm_parameter="inline_verify")
            return
    
    string = query.query.strip().lower()
    if not string:
        # If no query, maybe show some trending or recent files, or a prompt
        await query.answer(results=[],
                           cache_time=0,
                           switch_pm_text="Type something to search!",
                           switch_pm_parameter="start")
        return

    offset = int(query.offset or 0)
    files, total, next_offset = await get_search_results(string, offset=offset, limit=MAX_BTN)

    results = []
    for file in files:
        # Ensure caption is a string, even if None
        file_caption_text = str(file.get('caption') or "") # Use .get() and default to empty string
        
        f_caption = FILE_CAPTION.format(
            file_name=file['file_name'],
            file_size=get_size(file['file_size']),
            caption=file_caption_text # Use the sanitized caption
        )
        reply_markup = get_reply_markup(string) # Pass the original query string for "Search Again"

        results.append(
            InlineQueryResultCachedDocument(
                title=file['file_name'],
                document_file_id=file['_id'],
                caption=f_caption,
                description=f'Size: {get_size(file["file_size"])}',
                reply_markup=reply_markup))

    if results:
        switch_pm_text = f"Results - {total}"
        if string:
            switch_pm_text += f' For: {string}'
        await query.answer(results=results,
                        is_personal = True,
                        cache_time=cache_time,
                        switch_pm_text=switch_pm_text,
                        switch_pm_parameter="start",
                        next_offset=str(next_offset))
    else:
        switch_pm_text = f'No Results'
        if string:
            switch_pm_text += f' For: {string}'
        await query.answer(results=[],
                           is_personal = True,
                           cache_time=cache_time,
                           switch_pm_text=switch_pm_text,
                           switch_pm_parameter="start")


def get_reply_markup(s):
    buttons = [[
        InlineKeyboardButton('🔎 Search Again', switch_inline_query_current_chat=s or '')
    ],[
        InlineKeyboardButton('⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️', url=UPDATES_LINK),
        InlineKeyboardButton('💡 Support Group 💡', url=SUPPORT_LINK)
    ]]
    return InlineKeyboardMarkup(buttons)
