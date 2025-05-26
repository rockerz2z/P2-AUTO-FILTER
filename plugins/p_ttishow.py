import random
import os
import sys
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from info import ADMINS, LOG_CHANNEL, PICS, SUPPORT_LINK, UPDATES_LINK, IS_VERIFY, VERIFY_TUTORIAL, VERIFY_EXPIRE
from database.users_chats_db import db
from utils import temp, get_settings, get_verify_status, update_verify_status, is_subscribed, is_premium
from Script import script
from datetime import datetime, timedelta


@Client.on_chat_member_updated()
async def welcome(bot, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return
    
    if message.new_chat_member and not message.old_chat_member: # New member joined
        user = message.new_chat_member.user
        if user.id == temp.ME: # Bot joined the group
            buttons = [[
                InlineKeyboardButton('ᴜᴘᴅᴀᴛᴇ', url=UPDATES_LINK),
                InlineKeyboardButton('ꜱᴜᴘᴘᴏʀᴛ', url=SUPPORT_LINK)
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            adder_mention = message.from_user.mention if message.from_user else "Dear"
            try:
                await bot.send_photo(chat_id=message.chat.id, photo=random.choice(PICS), caption=f"👋 Hello {adder_mention},\n\nThank you for adding me to the <b>'{message.chat.title}'</b> group, Don't forget to make me admin. If you want to know more ask the support group. 😘</b>", reply_markup=reply_markup)
            except Exception as e:
                print(f"Error sending welcome photo: {e}")
                # Fallback to text message if photo fails
                await bot.send_message(chat_id=message.chat.id, text=f"👋 Hello {adder_mention},\n\nThank you for adding me to the <b>'{message.chat.title}'</b> group, Don't forget to make me admin. If you want to know more ask the support group. 😘</b>", reply_markup=reply_markup)

            if not await db.get_chat(message.chat.id):
                total = await db.add_chat(message.chat.id, message.chat.title)
                if LOG_CHANNEL:
                    try:
                        await bot.send_message(LOG_CHANNEL, f"Bot added to a new group: {message.chat.title}\nTotal groups: {total}")
                    except Exception as e:
                        print(f"Error sending log to channel: {e}")
        else: # Regular user joined
            settings = await get_settings(message.chat.id)
            if settings.get('welcome'):
                welcome_text = settings.get('welcome_text', script.WELCOME_MSG)
                user_mention = user.mention if user else "Dear" # Handle anonymous users
                welcome_msg = welcome_text.format(
                    id=user.id,
                    mention=user_mention,
                    chat_name=message.chat.title,
                    chat_id=message.chat.id,
                    first_name=user.first_name,
                    last_name=user.last_name or '',
                    username=user.username or ''
                )
                await message.reply_text(welcome_msg, disable_web_page_preview=True)
    elif message.old_chat_member and not message.new_chat_member: # Member left
        # You can add a goodbye message here if desired
        pass


@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users(bot, message):
    raju = await message.reply('Getting list of users')
    users = await db.get_all_users()
    out = "Users saved in database are:\n\n"
    for user in users:
        try:
            u = await bot.get_users(user['id'])
            out += f"**Name:** {u.mention}\n**ID:** `{u.id}`"
            if user['is_banned']:
                out += ' (Banned)'
            out += '\n\n'
        except Exception: # Handle cases where user might not be accessible
            out += f"**ID:** `{user['id']}` (Account Deleted/Inaccessible)"
            if user['is_banned']:
                out += ' (Banned)'
            out += '\n\n'
            
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
    chats = await db.get_all_chats()
    out = "Chats saved in database are:\n\n"
    for chat in chats:
        out += f"**Title:** {chat.get('title', 'N/A')}\n**ID:** `{chat['id']}`" # Use .get() for title safety
        if chat.get('chat_status') and chat['chat_status'].get('is_disabled'): # Use .get() for safety
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


@Client.on_chat_join_request()
async def join_reqs(client, message: ChatJoinRequest):
    stg = db.get_bot_sttgs()
    request_channel_id = stg.get('REQUEST_FORCE_SUB_CHANNELS')
    if request_channel_id and message.chat.id == int(request_channel_id):
        # Add user to database if not exists
        if not await db.get_user(message.from_user.id): # Using get_user for consistency
            total = await db.add_user(message.from_user.id, message.from_user.first_name)
            if IS_VERIFY: # If verification is on, mark as not verified by default for new users
                await update_verify_status(message.from_user.id, {'is_verified': False, 'last_verified': datetime.now() - timedelta(days=2)})

        # Force Subscription Check
        is_fsub = await is_subscribed(client, message.from_user)
        if is_fsub is not True:
            buttons = [[
                InlineKeyboardButton('Join Updates Channel', url=UPDATES_LINK),
                InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
            ]]
            return await message.deny(
                text=f"You need to join our updates channel and support group to proceed.\n\n{script.FORCE_SUB_TEXT}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Verification Check
        if IS_VERIFY:
            verify_status = await get_verify_status(message.from_user.id)
            if not verify_status.get('is_verified') and not await is_premium(message.from_user.id, client):
                buttons = [[
                    InlineKeyboardButton('Verify Now', callback_data='verify_user#request_join')
                ]]
                return await message.deny(
                    text=f"You need to verify yourself to join this chat.\n\n{script.VERIFY_TXT}",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )

        # All checks passed, approve join request
        await message.approve()
        await client.send_message(message.from_user.id, f"Welcome to **{message.chat.title}**!\n\n{script.JOIN_WELCOME_MESSAGE}")


@Client.on_message(filters.command('verify'))
async def start_verify(bot, message):
    if not IS_VERIFY:
        return await message.reply_text('Verification is currently disabled.')
    
    verify_status = await get_verify_status(message.from_user.id)
    if verify_status.get('is_verified') and (datetime.now() - verify_status.get('last_verified', datetime.min)).total_seconds() < VERIFY_EXPIRE:
        return await message.reply_text("You are already verified for today!")

    if VERIFY_TUTORIAL:
        await message.reply_text(f"Please follow the tutorial to verify yourself: {VERIFY_TUTORIAL}", disable_web_page_preview=True)
    
    buttons = [[
        InlineKeyboardButton('Verify Now', callback_data='verify_user#start_cmd')
    ]]
    await message.reply_photo(photo=random.choice(PICS), caption=script.VERIFY_TXT, reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r'^verify_user'))
async def auto_verify(bot, query):
    if not IS_VERIFY:
        return await query.answer('Verification is currently disabled.', show_alert=True)

    user_id = query.from_user.id
    verify_status = await get_verify_status(user_id)
    
    current_time = datetime.now()
    last_verified = verify_status.get('last_verified', datetime.min)

    # Check if already verified within the expiry period
    if verify_status.get('is_verified') and (current_time - last_verified).total_seconds() < VERIFY_EXPIRE:
        await query.answer("You are already verified for today!", show_alert=True)
        return await query.message.delete()

    # Perform verification (mark as verified and update timestamp)
    await update_verify_status(user_id, {'is_verified': True, 'last_verified': current_time})
    await query.answer("You have been successfully verified!", show_alert=True)
    await query.message.edit_text("Verification successful! You can now use the bot features.")
