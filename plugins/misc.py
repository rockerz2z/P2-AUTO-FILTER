from info import ADMINS
from speedtest import Speedtest, ConfigRetrievalError, SpeedtestBestServerFailure
from pyrogram import Client, filters, enums
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_size, get_readable_time
from datetime import datetime
import os
import time


@Client.on_message(filters.command('id'))
async def showid(client, message):
    chat_type = message.chat.type
    replied_to_msg = message.reply_to_message
    
    if replied_to_msg:
        if replied_to_msg.from_user:
            user_id_text = f"★ User ID of replied user: <code>{replied_to_msg.from_user.id}</code>"
        elif replied_to_msg.sender_chat and replied_to_msg.sender_chat.type == enums.ChatType.CHANNEL:
            user_id_text = f"★ Channel ID of forwarded message: <code>{replied_to_msg.sender_chat.id}</code>"
        else:
            user_id_text = "Could not determine ID for the replied message."
        
        await message.reply_text(user_id_text)
        return

    if chat_type == enums.ChatType.PRIVATE:
        await message.reply_text(f'★ User ID: <code>{message.from_user.id}</code>')

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        await message.reply_text(f'★ Group ID: <code>{message.chat.id}</code>')

    elif chat_type == enums.ChatType.CHANNEL:
        await message.reply_text(f'★ Channel ID: <code>{message.chat.id}</code>')


@Client.on_message(filters.command('speedtest') & filters.user(ADMINS))
async def speedtest(client, message):
    # from - https://github.com/weebzone/WZML-X/blob/master/bot/modules/speedtest.py
    speed = "<b>Speedtest Results</b>\n\n"
    status_message = await message.reply_text("`Running Speed Test . . .`")

    try:
        test = Speedtest()
        # Adding more specific exception handling for speedtest setup
        try:
            test.get_best_server()
        except ConfigRetrievalError:
            await status_message.edit("Failed to retrieve speedtest configuration. Please try again later.")
            return
        except SpeedtestBestServerFailure:
            await status_message.edit("Failed to find best server for speedtest. Please try again later.")
            return
        except Exception as e:
            await status_message.edit(f"An unexpected error occurred during speedtest setup: {e}")
            return

        start_time = time.time()
        test.download()
        end_time = time.time()
        download_time = round(end_time - start_time, 2)
        
        start_time = time.time()
        test.upload()
        end_time = time.time()
        upload_time = round(end_time - start_time, 2)

        test.results.share()
        result = test.results.dict()

        download_speed = get_size(result['download'])
        upload_speed = get_size(result['upload'])
        ping_time = result['ping']
        client_location = result['client']['country']
        client_isp = result['client']['isp']
        server_location = result['server']['country']
        server_sponsor = result['server']['sponsor']
        
        speed += f"<b>Download:</b> {download_speed}\n"
        speed += f"<b>Upload:</b> {upload_speed}\n"
        speed += f"<b>Ping:</b> {ping_time}\n"
        speed += f"<b>ISP:</b> {client_isp}\n"
        speed += f"<b>Server:</b> {server_sponsor} ({server_location})\n"
        speed += f"<b>Download Time:</b> {get_readable_time(download_time)}\n"
        speed += f"<b>Upload Time:</b> {get_readable_time(upload_time)}\n"

        await status_message.edit(speed)

    except Exception as e:
        await status_message.edit(f"Speedtest failed due to an error: {e}")


@Client.on_message(filters.command('info'))
async def user_info(client, message):
    # from https://github.com/weebzone/WZML-X/blob/master/bot/modules/info.py
    status_message = await message.reply("`Workspaceing info...`")
    from_user = None
    if message.reply_to_message:
        from_user = message.reply_to_message.from_user
    elif len(message.command) == 2:
        try:
            from_user = await client.get_users(int(message.command[1]))
        except Exception:
            try:
                from_user = await client.get_users(message.command[1])
            except Exception as e:
                return await status_message.edit(f"`Error: {e}`")
    elif not message.reply_to_message and len(message.command) != 2:
        from_user = message.from_user
    
    if not from_user:
        return await status_message.edit("User not found or no user specified.")

    message_out_str = ""
    message_out_str += f"<b>First Name:</b> {from_user.first_name}\n"
    if from_user.last_name:
        message_out_str += f"<b>Last Name:</b> {from_user.last_name}\n"
    message_out_str += f"<b>Telegram ID:</b> <code>{from_user.id}</code>\n"
    if from_user.username:
        message_out_str += f"<b>Username:</b> @{from_user.username}\n"
    message_out_str += f"<b>Is Bot:</b> {from_user.is_bot}\n"
    message_out_str += f"<b>Status:</b> {last_online(from_user)}\n"
    message_out_str += f"<b>Profile Link:</b> {from_user.mention}\n"
    if from_user.dc_id:
        message_out_str += f"<b>DC ID:</b> {from_user.dc_id}\n"
    if from_user.photo:
        message_out_str += f"<b>User Profile Photo:</b> <a href=\"https://t.me/{client.me.username}?start=info_{from_user.id}\">Link</a>\n" # Assuming a link can be generated
    
    # Try to get chat member status if in a group
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        try:
            chat_member = await message.chat.get_member(from_user.id)
            joined_date = chat_member.joined_date.strftime("%Y-%m-%d %H:%M:%S") if chat_member.joined_date else "N/A"
            message_out_str += (
                f"<b>Joined This Chat on:</b> <code>"
                f"{joined_date}"
                f"</code>\n"
            )
        except UserNotParticipant:
            pass # User is not a participant in this chat

    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(
            message=chat_photo.big_file_id
        )
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        os.remove(local_user_photo)
    else:
        await message.reply_text(
            text=message_out_str,
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()


def last_online(from_user):
    time_str = ""
    if from_user.is_bot:
        time_str += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time_str += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time_str += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time_str += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time_str += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time_str += "Online"
    else:
        # Convert datetime object to string if it exists
        if from_user.status:
            time_str += from_user.status.strftime("%Y-%m-%d %H:%M:%S") # Format datetime object
        else:
            time_str += "Unknown" # Fallback if status is none or unrecognized
    return time_str
