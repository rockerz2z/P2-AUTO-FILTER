import os
import random
import string
import asyncio
from time import time as time_now
from time import monotonic
import datetime
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from database.ia_filterdb import db_count_documents, second_db_count_documents, get_file_details, delete_files
from database.users_chats_db import db
from datetime import datetime, timedelta
from info import IS_PREMIUM, PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME, URL, BIN_CHANNEL, SECOND_FILES_DATABASE_URL, STICKERS, INDEX_CHANNELS, ADMINS, IS_VERIFY, VERIFY_TUTORIAL, VERIFY_EXPIRE, SHORTLINK_API, SHORTLINK_URL, DELETE_TIME, SUPPORT_LINK, UPDATES_LINK, LOG_CHANNEL, PICS, IS_STREAM, REACTIONS, PM_FILE_DELETE_TIME
from utils import is_premium, upload_image, get_settings, get_size, is_subscribed, is_check_admin, get_shortlink, get_verify_status, update_verify_status, save_group_settings, temp, get_readable_time, get_wish, get_seconds, is_check_admin_in_db

async def del_stk(s):
    await asyncio.sleep(3)
    await s.delete()

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await db.total_chat_count()
            await db.add_chat(message.chat.id, message.chat.title)
            await client.send_message(LOG_CHANNEL, f"#NEW_GROUP: \n\nNew Group Name - `{message.chat.title}`\nGroup Id - `{message.chat.id}`\nTotal Groups - `{total}`")
            return await message.reply_text(f"👋 Hello {message.from_user.mention},\n\nThank you for adding me to the **{message.chat.title}** group, Don't forget to make me admin. If you want to know more ask the support group.", 
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Support Group", url=SUPPORT_LINK)
                ]]))
        return await message.reply_text(f"👋 Hello {message.from_user.mention},\n\nThank you for adding me to the **{message.chat.title}** group, Don't forget to make me admin. If you want to know more ask the support group.", 
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Support Group", url=SUPPORT_LINK)
            ]]))
    
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, f"#NEW_USER: \n\nNew User - {message.from_user.mention}\nID - `{message.from_user.id}`")

    if IS_VERIFY and not await is_premium(message.from_user.id, client):
        verify_status = await get_verify_status(message.from_user.id)
        if not verify_status['is_verified']:
            return await message.reply_text(f"Hello {message.from_user.mention},\n\n**You're not verified today**, So you can't use bot currently.\n\nPress below button to verify now 👇", 
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Verify Now", callback_data='verify_btn')
                ]]))
    
    btn = [[
        InlineKeyboardButton("🔎 Search Inline", switch_inline_query_current_chat="")
    ],[
        InlineKeyboardButton("⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️", url=UPDATES_LINK),
        InlineKeyboardButton("💡 Support Group 💡", url=SUPPORT_LINK)
    ]]
    await message.reply_photo(photo=random.choice(PICS), caption=script.START_MSG.format(message.from_user.mention, get_wish()), reply_markup=InlineKeyboardMarkup(btn))


@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def get_stats(bot, message):
    if not await is_check_admin_in_db(bot, message.chat.id, message.from_user.id): # Check if user is admin in db
        return await message.reply_text("You are not an admin to use this command.")

    stats_msg = await message.reply_text("Getting stats...")
    total_users = await db.total_users_count()
    total_chats = await db.total_chat_count()
    total_files = await db_count_documents()
    total_second_files = await second_db_count_documents() if SECOND_FILES_DATABASE_URL else 0
    premium_users = await db.get_premium_count()
    files_db_size = await db.get_files_db_size()
    second_files_db_size = await db.get_second_files_db_size()
    data_db_size = await db.get_data_db_size()

    current_time = datetime.now()
    up_time_sec = (current_time - temp.START_TIME).total_seconds()
    
    total_free_users = total_users - premium_users

    stats = f"""
**Bot Stats:**

• **Total Users:** `{total_users}`
    - Free: `{total_free_users}`
    - Premium: `{premium_users}`
• **Total Chats:** `{total_chats}`
• **Total Files:** `{total_files + total_second_files}`
    - Primary DB Files: `{total_files}`
    - Secondary DB Files: `{total_second_files}` (if enabled)

**Database Sizes:**
• **Primary Files DB Size:** `{get_size(files_db_size)}`
• **Secondary Files DB Size:** `{get_size(second_files_db_size)}` (if enabled)
• **Data DB Size:** `{get_size(data_db_size)}`

**Uptime:** `{get_readable_time(up_time_sec)}`
"""
    await stats_msg.edit_text(stats)


@Client.on_message(filters.command("delete") & filters.user(ADMINS))
async def delete_file(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a file_name to delete. Or reply to a file to delete using its file_name")
    
    if message.reply_to_message and message.reply_to_message.document:
        file_name = message.reply_to_message.document.file_name
    elif message.reply_to_message and message.reply_to_message.caption:
        file_name = message.reply_to_message.caption
    else:
        file_name = " ".join(message.command[1:])
    
    deleted_count = await delete_files(file_name)
    
    if deleted_count > 0:
        await message.reply_text(f"Successfully deleted {deleted_count} files with name `{file_name}` from database.")
    else:
        await message.reply_text(f"No files found with name `{file_name}` to delete.")

@Client.on_message(filters.command('status') & filters.user(ADMINS))
async def get_status(bot, message):
    stg = await db.get_bot_sttgs()
    if not stg:
        stg = db.default_setgs # Fallback if no settings are saved
        
    await message.reply_text(f"""
Bot Global Settings:

Auto Filter: `{stg.get('auto_filter', False)}`
File Secure: `{stg.get('file_secure', False)}`
IMDB: `{stg.get('imdb', False)}`
Spell Check: `{stg.get('spell_check', False)}`
Auto Delete: `{stg.get('auto_delete', False)}`
Welcome: `{stg.get('welcome', False)}`
Welcome Text: `{stg.get('welcome_text', 'No welcome text set')}`
IMDB Template: `{stg.get('template', 'No template set')}`
Caption: `{stg.get('caption', 'No caption set')}`
URL: `{stg.get('url', 'No URL set')}`
API: `{stg.get('api', 'No API key set')}`
Shortlink: `{stg.get('shortlink', False)}`
Tutorial: `{stg.get('tutorial', 'No tutorial set')}`
Links Mode: `{stg.get('links', False)}`
PM File Delete Time: `{PM_FILE_DELETE_TIME}` seconds

"""
    )


@Client.on_message(filters.command('ban') & filters.user(ADMINS))
async def ban(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a user ID or reply to a user to ban him.")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.full_name
        if len(message.command) > 1:
            ban_reason = " ".join(message.command[1:])
        else:
            ban_reason = "No Reason"
    else:
        try:
            user_id = int(message.text.split(" ", 1)[1].split(" ", 1)[0])
            if len(message.text.split(" ", 2)) > 2:
                ban_reason = message.text.split(" ", 2)[2]
            else:
                ban_reason = "No Reason"
            
            try:
                user_name = (await bot.get_users(user_id)).full_name
            except:
                user_name = f"User {user_id}" # Fallback if user not found
                
        except (ValueError, IndexError):
            return await message.reply_text("Invalid User ID or format. Use /ban <user_id> [reason] or reply to a user.")

    if user_id in ADMINS:
        return await message.reply_text("You can't ban an admin!")

    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, user_name) # Ensure user exists in DB before banning
    
    ban_status = await db.get_ban_status(user_id)
    if ban_status['is_banned']:
        return await message.reply_text(f"This user is already banned.\nReason: {ban_status['ban_reason']}")

    await db.ban_user(user_id, ban_reason)
    temp.BANNED_USERS.append(user_id)
    await message.reply_text(f"Successfully banned {user_name} (ID: {user_id}) from using the bot.\nReason: {ban_reason}")


@Client.on_message(filters.command('unban') & filters.user(ADMINS))
async def unban(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a user ID or reply to a user to unban him.")

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.full_name
    else:
        try:
            user_id = int(message.text.split(" ", 1)[1])
            try:
                user_name = (await bot.get_users(user_id)).full_name
            except:
                user_name = f"User {user_id}"
        except (ValueError, IndexError):
            return await message.reply_text("Invalid User ID or format. Use /unban <user_id> or reply to a user.")

    if not await db.is_user_exist(user_id):
        return await message.reply_text("This user is not in my database.")
    
    ban_status = await db.get_ban_status(user_id)
    if not ban_status['is_banned']:
        return await message.reply_text("This user is not currently banned.")

    await db.remove_ban(user_id)
    if user_id in temp.BANNED_USERS:
        temp.BANNED_USERS.remove(user_id)
    await message.reply_text(f"Successfully unbanned {user_name} (ID: {user_id}).")


@Client.on_message(filters.command('chatban') & filters.user(ADMINS))
async def chat_ban(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a chat ID to disable it. Or reply to a group message.")
    
    if message.reply_to_message and message.reply_to_message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        chat_id = message.reply_to_message.chat.id
        chat_name = message.reply_to_message.chat.title
        if len(message.command) > 1:
            reason = " ".join(message.command[1:])
        else:
            reason = "No Reason"
    else:
        try:
            chat_id = int(message.text.split(" ", 1)[1].split(" ", 1)[0])
            if len(message.text.split(" ", 2)) > 2:
                reason = message.text.split(" ", 2)[2]
            else:
                reason = "No Reason"
            
            try:
                chat_name = (await bot.get_chat(chat_id)).title
            except:
                chat_name = f"Chat {chat_id}"
                
        except (ValueError, IndexError):
            return await message.reply_text("Invalid Chat ID or format. Use /chatban <chat_id> [reason] or reply to a group message.")

    if not await db.get_chat(chat_id): # Check if chat exists in DB, add if not
        await db.add_chat(chat_id, chat_name)
    
    chat_status = await db.get_chat(chat_id)
    if chat_status and chat_status['is_disabled']:
        return await message.reply_text(f"This chat is already disabled.\nReason: {chat_status['reason']}")

    await db.disable_chat(chat_id, reason)
    temp.BANNED_CHATS.append(chat_id)
    await message.reply_text(f"Successfully disabled chat {chat_name} (ID: {chat_id}).\nReason: {reason}")


@Client.on_message(filters.command('chatunban') & filters.user(ADMINS))
async def chat_unban(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a chat ID to enable it. Or reply to a group message.")

    if message.reply_to_message and message.reply_to_message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        chat_id = message.reply_to_message.chat.id
        chat_name = message.reply_to_message.chat.title
    else:
        try:
            chat_id = int(message.text.split(" ", 1)[1])
            try:
                chat_name = (await bot.get_chat(chat_id)).title
            except:
                chat_name = f"Chat {chat_id}"
        except (ValueError, IndexError):
            return await message.reply_text("Invalid Chat ID or format. Use /chatunban <chat_id> or reply to a group message.")
    
    chat_status = await db.get_chat(chat_id)
    if not chat_status or not chat_status['is_disabled']:
        return await message.reply_text("This chat is not currently disabled.")

    await db.re_enable_chat(chat_id)
    if chat_id in temp.BANNED_CHATS:
        temp.BANNED_CHATS.remove(chat_id)
    await message.reply_text(f"Successfully re-enabled chat {chat_name} (ID: {chat_id}).")


@Client.on_message(filters.command('del_premium') & filters.user(ADMINS))
async def del_premium(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Give a user ID or reply to a user to remove premium.")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.full_name
    else:
        try:
            user_id = int(message.text.split(" ", 1)[1])
            try:
                user_name = (await bot.get_users(user_id)).full_name
            except:
                user_name = f"User {user_id}"
        except (ValueError, IndexError):
            return await message.reply_text("Invalid User ID or format. Use /del_premium <user_id> or reply to a user.")
    
    plan_status = await db.get_plan(user_id)
    if not plan_status['premium']:
        return await message.reply_text("This user is not a premium user.")
    
    plan_status['premium'] = False
    plan_status['plan'] = ''
    plan_status['expire'] = ''
    plan_status['trial'] = False
    await db.update_plan(user_id, plan_status)
    await message.reply_text(f"Successfully removed premium status for {user_name} (ID: {user_id}).")


@Client.on_message(filters.command('add_premium') & filters.user(ADMINS))
async def add_premium(bot, message):
    if len(message.command) < 3:
        return await message.reply_text("Usage: /add_premium <user_id/reply> <days> [plan_name]")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_name = message.reply_to_message.from_user.full_name
        days_str = message.command[1]
        plan_name = " ".join(message.command[2:]) if len(message.command) > 2 else "Custom"
    else:
        try:
            user_id = int(message.command[1])
            days_str = message.command[2]
            plan_name = " ".join(message.command[3:]) if len(message.command) > 3 else "Custom"
            try:
                user_name = (await bot.get_users(user_id)).full_name
            except:
                user_name = f"User {user_id}"
        except (ValueError, IndexError):
            return await message.reply_text("Invalid arguments. Usage: /add_premium <user_id/reply> <days> [plan_name]")
    
    try:
        days = int(days_str)
        if days <= 0:
            raise ValueError
    except ValueError:
        return await message.reply_text("Invalid number of days. Please provide a positive integer.")
    
    plan_status = await db.get_plan(user_id)
    if not plan_status:
        plan_status = db.default_prm.copy() # Start with default if no existing plan

    plan_status['premium'] = True
    plan_status['plan'] = plan_name
    
    # Calculate expiration time
    expire_date = datetime.now() + timedelta(days=days)
    plan_status['expire'] = expire_date.strftime("%d-%m-%Y %I:%M %p")
    plan_status['trial'] = False # Assuming adding premium means not a trial

    await db.update_plan(user_id, plan_status)
    await message.reply_text(f"Successfully added {days} days premium for {user_name} (ID: {user_id}).\nPlan: {plan_name}\nExpires on: {plan_status['expire']}")


@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users(bot, message):
    raju = await message.reply('Getting list of users')
    users_cursor = db.get_all_users() # This returns an AsyncIOMotorCursor
    users_list = []
    async for user in users_cursor: # Use async for to iterate
        users_list.append(user['id'])

    out = "Users saved in database are:\n\n"
    for user_id in users_list:
        try:
            u = await bot.get_users(user_id)
            out += f"{u.mention} : {user_id}\n"
        except Exception:
            out += f"{user_id} (User not found/deleted)\n" # Handle cases where user might not be resolvable
    try:
        await raju.edit_text(out)
    except MessageTooLong:
        with open('users.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('users.txt', caption="List of users")
        await raju.delete()
        os.remove('users.txt')


@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats(bot, message):
    raju = await message.reply('Getting list of chats')
    chats_cursor = db.get_all_chats() # This returns an AsyncIOMotorCursor
    chats_list = []
    async for chat in chats_cursor: # Use async for to iterate
        chats_list.append(chat) # Append the whole chat document

    out = "Chats saved in database are:\n\n"
    for chat_data in chats_list:
        out += f"**Title:** {chat_data['title']}\n**ID:** `{chat_data['id']}`"
        if chat_data['chat_status']['is_disabled']:
            out += ' (Disabled Chat)'
        out += '\n\n'
    try:
        await raju.edit_text(out)
    except MessageTooLong:
        with open('chats.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('chats.txt', caption="List of chats")
        await raju.delete()
        os.remove('chats.txt')


@Client.on_message(filters.command('premium_users') & filters.user(ADMINS))
async def list_premium_users(bot, message):
    tx = await message.reply('Getting list of premium users')
    # Use async for to iterate over the cursor returned by get_premium_users
    premium_users_list = [i['id'] async for i in db.get_premium_users() if i['status']['premium']]
    
    t = 'Premium users saved in database are:\n\n'
    for p_user_id in premium_users_list:
        try:
            u = await bot.get_users(p_user_id)
            t += f"{u.mention} : {p_user_id}\n"
        except Exception: # Catch any error during get_users, e.g., user deleted
            t += f"{p_user_id} (User not found/deleted)\n"
    
    try:
        await tx.edit_text(t)
    except MessageTooLong:
        with open('premium_users.txt', 'w+') as outfile:
            outfile.write(t)
        await message.reply_document('premium_users.txt', caption="List of Premium Users")
        await tx.delete()
        os.remove('premium_users.txt')


@Client.on_message(filters.command('set_fsub') & filters.user(ADMINS))
async def set_fsub(bot, message):
    try:
        _, ids = message.text.split(' ', 1)
    except ValueError:
        return await message.reply('Usage: /set_fsub -100xxx -100xxx')
    title = ""
    for id_str in ids.split(' '):
        try:
            chat = await bot.get_chat(int(id_str))
            title += f'{chat.title}\n'
        except Exception as e:
            return await message.reply(f'ERROR: Could not fetch chat for ID {id_str}: {e}')
    await db.update_bot_sttgs('FORCE_SUB_CHANNELS', ids)
    await message.reply(f'Added force subscribe channels:\n{title}')

        
@Client.on_message(filters.command('set_req_fsub') & filters.user(ADMINS))
async def set_req_fsub(bot, message):
    try:
        _, id_str = message.text.split(' ', 1)
    except ValueError:
        return await message.reply('Usage: /set_req_fsub <channel_id>')
    try:
        chat = await bot.get_chat(int(id_str))
        await db.update_bot_sttgs('REQUEST_FORCE_SUB_CHANNELS', id_str)
        await message.reply(f'Set request force subscribe channel to: {chat.title} (ID: {id_str})')
    except Exception as e:
        await message.reply(f'ERROR: Could not fetch chat for ID {id_str}: {e}')


@Client.on_message(filters.command('del_verify_link') & filters.user(ADMINS))
async def del_verify_link(bot, message):
    await db.del_join_req()
    await message.reply_text('Successfully deleted all verification links!')


@Client.on_message(filters.command('set_welcome') & filters.user(ADMINS))
async def set_welcome_text(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_welcome <your_welcome_text>\n\nUse {mention} for user mention.")
    
    welcome_text = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['welcome_text'] = welcome_text
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Welcome text updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('WELCOME_TEXT', welcome_text)
        return await message.reply_text(f"Global welcome text updated.")


@Client.on_message(filters.command('set_imdb_template') & filters.user(ADMINS))
async def set_imdb_template(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_imdb_template <your_template>\n\nUse {mention} for user mention, {title} for movie title, etc.")
    
    imdb_template = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['template'] = imdb_template
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"IMDB template updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('IMDB_TEMPLATE', imdb_template)
        return await message.reply_text(f"Global IMDB template updated.")


@Client.on_message(filters.command('set_caption') & filters.user(ADMINS))
async def set_caption(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_caption <your_caption>\n\nUse {file_name}, {file_size} etc.")
    
    caption = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['caption'] = caption
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Caption updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('FILE_CAPTION', caption)
        return await message.reply_text(f"Global file caption updated.")


@Client.on_message(filters.command('set_tutorial') & filters.user(ADMINS))
async def set_tutorial(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_tutorial <your_tutorial_link>")
    
    tutorial_link = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['tutorial'] = tutorial_link
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Tutorial link updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('TUTORIAL', tutorial_link)
        return await message.reply_text(f"Global tutorial link updated.")


@Client.on_message(filters.command('set_url') & filters.user(ADMINS))
async def set_url(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_url <your_shortener_url>")
    
    url = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['url'] = url
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Shortener URL updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('SHORTLINK_URL', url)
        return await message.reply_text(f"Global shortener URL updated.")


@Client.on_message(filters.command('set_shortlink_api') & filters.user(ADMINS))
async def set_shortlink_api(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_shortlink_api <your_shortener_api_key>")
    
    api_key = message.text.split(" ", 1)[1]
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['api'] = api_key
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Shortener API key updated for this group.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs('SHORTLINK_API', api_key)
        return await message.reply_text(f"Global shortener API key updated.")


@Client.on_message(filters.command('set_filter') & filters.user(ADMINS))
async def set_filter(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_filter <filter_type> [on/off]\nAvailable types: auto_filter, file_secure, imdb, spell_check, auto_delete, welcome, shortlink, link_mode")
    
    try:
        _, filter_type, status_str = message.text.split(" ", 2)
        status = status_str.lower() == 'on'
    except ValueError:
        return await message.reply_text("Invalid usage. Usage: /set_filter <filter_type> [on/off]")
    
    if filter_type not in ['auto_filter', 'file_secure', 'imdb', 'spell_check', 'auto_delete', 'welcome', 'shortlink', 'link_mode']:
        return await message.reply_text("Invalid filter type.")
    
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings[filter_type] = status
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"{filter_type} for this group turned {'ON' if status else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        await db.update_bot_sttgs(filter_type.upper(), status) # Assuming global settings vars are uppercase
        return await message.reply_text(f"Global {filter_type} turned {'ON' if status else 'OFF'}.")


@Client.on_message(filters.command('toggle_imdb') & filters.user(ADMINS))
async def toggle_imdb(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['imdb'] = not settings.get('imdb', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"IMDB for this group turned {'ON' if settings['imdb'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('IMDB', False)
        await db.update_bot_sttgs('IMDB', not current_status)
        return await message.reply_text(f"Global IMDB turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_spell_check') & filters.user(ADMINS))
async def toggle_spell_check(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['spell_check'] = not settings.get('spell_check', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Spell check for this group turned {'ON' if settings['spell_check'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('SPELL_CHECK', False)
        await db.update_bot_sttgs('SPELL_CHECK', not current_status)
        return await message.reply_text(f"Global spell check turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_secure') & filters.user(ADMINS))
async def toggle_secure(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['file_secure'] = not settings.get('file_secure', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"File secure for this group turned {'ON' if settings['file_secure'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('PROTECT_CONTENT', False)
        await db.update_bot_sttgs('PROTECT_CONTENT', not current_status)
        return await message.reply_text(f"Global file secure turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_auto_delete') & filters.user(ADMINS))
async def toggle_auto_delete(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['auto_delete'] = not settings.get('auto_delete', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Auto delete for this group turned {'ON' if settings['auto_delete'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('AUTO_DELETE', False)
        await db.update_bot_sttgs('AUTO_DELETE', not current_status)
        return await message.reply_text(f"Global auto delete turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_welcome') & filters.user(ADMINS))
async def toggle_welcome(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['welcome'] = not settings.get('welcome', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Welcome messages for this group turned {'ON' if settings['welcome'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('WELCOME', False)
        await db.update_bot_sttgs('WELCOME', not current_status)
        return await message.reply_text(f"Global welcome messages turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_shortlink') & filters.user(ADMINS))
async def toggle_shortlink(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['shortlink'] = not settings.get('shortlink', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Shortlink for this group turned {'ON' if settings['shortlink'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('SHORTLINK', False)
        await db.update_bot_sttgs('SHORTLINK', not current_status)
        return await message.reply_text(f"Global shortlink turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('toggle_link_mode') & filters.user(ADMINS))
async def toggle_link_mode(bot, message):
    chat_id = message.chat.id
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        settings = await db.get_settings(chat_id)
        settings['links'] = not settings.get('links', False)
        await db.update_settings(chat_id, settings)
        return await message.reply_text(f"Links mode for this group turned {'ON' if settings['links'] else 'OFF'}.")
    else:
        stg = await db.get_bot_sttgs()
        current_status = stg.get('LINK_MODE', False)
        await db.update_bot_sttgs('LINK_MODE', not current_status)
        return await message.reply_text(f"Global links mode turned {'ON' if not current_status else 'OFF'}.")


@Client.on_message(filters.command('connect') & filters.group)
async def connect_chat(bot, message):
    if not await is_check_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply_text("You are not an admin to use this command.")

    await db.add_connect(message.chat.id, message.from_user.id)
    await message.reply_text(f"Successfully connected {message.chat.title} to your account. Now you can use PM commands in this group.")


@Client.on_message(filters.command('disconnect') & filters.group)
async def disconnect_chat(bot, message):
    if not await is_check_admin(bot, message.chat.id, message.from_user.id):
        return await message.reply_text("You are not an admin to use this command.")

    # Assuming add_connect is used to also remove if called with appropriate logic or a specific disconnect function exists.
    # If the intent is to remove a connection, your db class needs a disconnect method.
    # For now, if db.add_connect also handles removal, this is fine.
    # If not, this needs to be clarified or a new db method implemented.
    # Assuming db.add_connect (from users_chats_db) now handles adding to a set,
    # so a disconnect would need a corresponding `remove_connect` method in users_chats_db.
    # Given the previous `add_connect` logic, there's no direct removal.
    # For now, I'll assume the provided `add_connect` is only for adding.
    # If a disconnect feature is desired, `users_chats_db.py` needs a `remove_connect` method.
    await message.reply_text("This command is not fully implemented for disconnection. Please check `users_chats_db.py` for a `remove_connect` function.")


@Client.on_message(filters.command('connections') & filters.private)
async def list_connections(bot, message):
    connections = await db.get_connections(message.from_user.id)
    if not connections:
        return await message.reply_text("You have no connected groups.")
    
    text = "Your connected groups:\n\n"
    for chat_id in connections:
        try:
            chat = await bot.get_chat(chat_id)
            text += f"- {chat.title} (`{chat_id}`)\n"
        except Exception:
            text += f"- Unknown chat (`{chat_id}`) - Likely left or deleted.\n"
    
    await message.reply_text(text)


@Client.on_message(filters.command('set_pm_delete_time') & filters.user(ADMINS))
async def set_pm_delete_time(bot, message):
    if len(message.command) == 1:
        return await message.reply_text("Usage: /set_pm_delete_time <seconds>\n\nSet to 0 to disable auto delete.")
    
    try:
        delete_time_str = message.text.split(" ", 1)[1]
        delete_time_seconds = int(delete_time_str)
        if delete_time_seconds < 0:
            raise ValueError
    except ValueError:
        return await message.reply_text("Invalid time. Please provide a non-negative integer for seconds.")
    
    await db.update_bot_sttgs('PM_FILE_DELETE_TIME', delete_time_seconds)
    if delete_time_seconds == 0:
        await message.reply_text("PM auto-delete for files has been disabled.")
    else:
        await message.reply_text(f"PM auto-delete for files set to {delete_time_seconds} seconds.")
