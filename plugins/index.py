import re
import time
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified, ChannelPrivate, ChatWriteForbidden
from info import ADMINS, INDEX_EXTENSIONS
from database.ia_filterdb import save_file
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time

lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    _, ident, chat, lst_msg_id, skip = query.data.split("#")
    if ident == 'yes':
        msg = query.message
        await msg.edit("Starting Indexing...")
        try:
            chat = int(chat)
        except ValueError: # Catch specific error for int conversion
            chat = chat # Keep as is if it's a string (e.g., username)
        except Exception as e:
            return await msg.edit(f"An unexpected error occurred while parsing chat ID: {e}")
        
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip))
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("Trying to cancel Indexing...")


@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('Wait until previous process complete.')
    i = await message.reply("Forward last message or send last message link.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await i.delete()
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text
            if "t.me/c/" in msg_link:
                chat = int("-100" + msg_link.split("/")[-2])
                lst_msg_id = int(msg_link.split("/")[-1])
            else:
                chat = msg_link.split("/")[-2]
                lst_msg_id = int(msg_link.split("/")[-1])
            await message.reply_text(f'Do you want to index from this chat **{chat}** from message **{lst_msg_id}**?', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Yes', callback_data=f'index#yes#{chat}#{lst_msg_id}#{0}'), InlineKeyboardButton('No', callback_data='index#no')]]))
        except ValueError: # Catch specific error for int conversion
            return await message.reply_text("Invalid message link provided. Please provide a valid Telegram message link.")
        except Exception as e: # Catch other unexpected errors
            return await message.reply_text(f"An error occurred while parsing the message link: {e}")

    else:
        if not msg.empty and msg.media: # Changed to check for message.empty
            lst_msg_id = msg.id
            chat = msg.chat.id
            await message.reply_text(f'Do you want to index from this chat **{chat}** from message **{lst_msg_id}**?', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Yes', callback_data=f'index#yes#{chat}#{lst_msg_id}#{0}'), InlineKeyboardButton('No', callback_data='index#no')]]))
        else:
            await message.reply_text('Failed to get message. Make sure the message is a valid message or link.')


async def index_files_to_db(lst_msg_id, chat, msg, bot, skip):
    async with lock:
        total_files = 0
        duplicate = 0
        errors = 0
        deleted = 0
        no_media = 0
        unsupported = 0
        badfiles = 0
        start_time = time.time()
        
        current_id = lst_msg_id
        while True:
            if temp.CANCEL:
                await msg.reply('Index canceled.')
                break
            try:
                message = await bot.get_messages(chat_id=chat, message_ids=current_id)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except ChannelPrivate:
                await msg.edit('Given channel is private. I can\'t access messages from private channels.')
                break
            except ChatWriteForbidden:
                await msg.edit('I am banned from this chat.')
                break
            except Exception as e:
                # Handle cases where message might be deleted or inaccessible
                if "messages not found" in str(e).lower() or "can't access the chat" in str(e).lower():
                    deleted += 1
                else:
                    errors += 1
                current_id -= 1
                continue

            if not message:
                break
            
            if message.empty: # Check for empty messages explicitly
                deleted += 1
                current_id -= 1
                continue

            if not message.media:
                no_media += 1
                current_id -= 1
                continue
            
            # Check for supported media types
            if message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                unsupported += 1
                current_id -= 1
                continue
            
            media = getattr(message, message.media.value, None)
            if not media:
                unsupported += 1
                current_id -= 1
                continue
            
            if not (str(media.file_name).lower()).endswith(tuple(INDEX_EXTENSIONS)):
                unsupported += 1
                current_id -= 1
                continue

            media.caption = message.caption
            # Sanitize file name for potential regex issues
            file_name = re.sub(r"[\s@\-_.]+", " ", str(media.file_name)).strip() # Improved sanitization
            
            sts = await save_file(media) # Assuming save_file returns 'suc', 'dup', 'err'
            if sts == 'suc':
                total_files += 1
            elif sts == 'dup':
                duplicate += 1
            elif sts == 'err':
                errors += 1
            
            current_id -= 1
            if not current_id % 20: # Update status every 20 messages
                try:
                    await msg.edit(f'Indexing messages from {chat} to database...\n\nTotal files saved: <code>{total_files}</code>\nDuplicate files skipped: <code>{duplicate}</code>\nDeleted messages skipped: <code>{deleted}</code>\nNon-media messages skipped: <code>{no_media + unsupported}</code>\nErrors occurred: <code>{errors}</code>\nBad files ignored: <code>{badfiles}</code>')
                except MessageNotModified:
                    pass # Ignore if message content is identical
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"Error updating message: {e}") # Log unexpected error for debugging

        time_taken = get_readable_time(time.time()-start_time)
        final_message = f'Successfully saved <code>{total_files}</code> to Database!\nCompleted in {time_taken}\n\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>\nUnsupported Media: <code>{unsupported}</code>\nErrors Occurred: <code>{errors}</code>\nBad Files Ignored: <code>{badfiles}</code>'
        
        try:
            await msg.edit(final_message)
        except MessageNotModified:
            pass # Ignore if message content is identical
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await msg.edit(final_message) # Try again after flood wait
        except Exception as e:
            await msg.reply(f'Index completed with some issues, but could not update final message due to error: {e}\n\n{final_message}')
