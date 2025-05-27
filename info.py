import re
from os import environ
import os
from Script import script # Make sure Script.py exists and has WELCOME_TXT
import logging

logger = logging.getLogger(__name__)

def is_enabled(type, value):
    data = environ.get(type, str(value))
    if data.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif data.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        logger.error(f'{type} is invalid, exiting now')
        exit()

def is_valid_ip(ip):
    ip_pattern = r'\b(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    return re.match(ip_pattern, ip) is not None

# Bot information
API_ID = environ.get('API_ID', '21388641')
if len(API_ID) == 0:
    logger.error('API_ID is missing, exiting now')
    exit()
else:
    API_ID = int(API_ID)
API_HASH = environ.get('API_HASH', '16d8a2b5e27a7c938ed4997089b2b512')
if len(API_HASH) == 0:
    logger.error('API_HASH is missing, exiting now')
    exit()
BOT_TOKEN = environ.get('BOT_TOKEN', '6795491118:AAHKtQ-1B5pQ-9P4S2v03R-R0a3qYj7oH-o')
if len(BOT_TOKEN) == 0:
    logger.error('BOT_TOKEN is missing, exiting now')
    exit()
PORT = environ.get('PORT', '8080')
if len(PORT) == 0:
    logger.error('PORT is missing, exiting now')
    exit()
else:
    PORT = int(PORT)

# Database information
DATA_DATABASE_URL = environ.get('DATA_DATABASE_URL', 'mongodb+srv://autofilter:autofilter@cluster0.10s3r.mongodb.net/?retryWrites=true&w=majority')
if len(DATA_DATABASE_URL) == 0:
    logger.error('DATA_DATABASE_URL is missing, exiting now')
    exit()

FILES_DATABASE_URL = environ.get('FILES_DATABASE_URL', 'mongodb+srv://autofilter:autofilter@cluster0.10s3r.mongodb.net/?retryWrites=true&w=majority')
if len(FILES_DATABASE_URL) == 0:
    logger.error('FILES_DATABASE_URL is missing, exiting now')
    exit()

SECOND_FILES_DATABASE_URL = environ.get('SECOND_FILES_DATABASE_URL', '') # Optional
DATABASE_NAME = environ.get('DATABASE_NAME', 'AutoFilterBot') # Added DATABASE_NAME

# Channels and groups
BIN_CHANNEL = environ.get('BIN_CHANNEL', '-1002047392683')
if len(BIN_CHANNEL) == 0:
    logger.error('BIN_CHANNEL is missing, exiting now')
    exit()
else:
    BIN_CHANNEL = int(BIN_CHANNEL)
INDEX_CHANNELS = [int(channel) for channel in environ.get('INDEX_CHANNELS', '-1002047392683').split()]
if len(INDEX_CHANNELS) == 0:
    logger.error('INDEX_CHANNELS is missing, exiting now')
    exit()
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1002047392683')) # Must be an integer
if not LOG_CHANNEL:
    logger.error('LOG_CHANNEL is missing or invalid, exiting now')
    exit()
SUPPORT_GROUP = int(environ.get('SUPPORT_GROUP', '-1002047392683')) # Must be an integer
if not SUPPORT_GROUP:
    logger.error('SUPPORT_GROUP is missing or invalid, exiting now')
    exit()

# Admin information
ADMINS = [int(admin) for admin in environ.get('ADMINS', '6795491118').split()]
if len(ADMINS) == 0:
    logger.error('ADMINS is missing, exiting now')
    exit()

# URL
URL = environ.get("URL", "https://onlinewatch.koyeb.app/")
if len(URL) == 0:
    logger.error('URL is missing, exiting now')
    exit()
else:
    if URL.startswith(('https://', 'http://')):
        if not URL.endswith("/"):
            URL += '/'
    elif is_valid_ip(URL):
        URL = f'http://{URL}/'
    else:
        logger.error('URL is not valid, exiting now')
        exit()

#start command reactions and sticker
REACTIONS = [reactions for reactions in environ.get('REACTIONS', '🤝 😇 🤗 😍 👍 🎅 😐 🥰 🤩 😱 🤣 😘 👏 😛 😈 🎉 ⚡️ 🫡 🤓 😎 🏆 🔥 🤭 🌚 🆒 👻 😁').split()]  # Multiple reactions can be used separated by space
STICKERS = [sticker for sticker in environ.get('STICKERS', 'CAACAgUAAxkBAAELTeJoJHtQsLxJJfkT4JakLxbUjcKz8wACjwIAAsnn6FVsAf5eBhi7Sh4E').split()]  # Multiple sticker can be used separated by space, use @idstickerbot for get sticker id

# for Premium 
IS_PREMIUM = is_enabled('IS_PREMIUM', True)
PRE_DAY_AMOUNT = int(environ.get('PRE_DAY_AMOUNT', '10')) # add amount in INR for premium charge pre day 
UPI_ID = environ.get("UPI_ID", "your_upi_id@paytm")
UPI_QR_CODE = environ.get("UPI_QR_CODE", "https://telegra.ph/file/af5b796d11100f2824907.jpg") # For example, a Telegraph link to the QR code image

# About bot
LONG_IMDB_DESCRIPTION = is_enabled('LONG_IMDB_DESCRIPTION', False)

# Added missing variables from users_chats_db.py import
IMDB_TEMPLATE = environ.get('IMDB_TEMPLATE', '')
WELCOME_TEXT = environ.get('WELCOME_TEXT', getattr(script, 'WELCOME_TXT', '')) # Using getattr for safety
LINK_MODE = is_enabled('LINK_MODE', True)
TUTORIAL = environ.get('TUTORIAL', '')
SHORTLINK_URL = environ.get('SHORTLINK_URL', '')
SHORTLINK_API = environ.get('SHORTLINK_API', '')
SHORTLINK = is_enabled('SHORTLINK', False)
FILE_CAPTION = environ.get('FILE_CAPTION', '')
IMDB = is_enabled('IMDB', True)
WELCOME = is_enabled('WELCOME', True)
SPELL_CHECK = is_enabled('SPELL_CHECK', True)
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False)
AUTO_FILTER = is_enabled('AUTO_FILTER', True)
AUTO_DELETE = is_enabled('AUTO_DELETE', False)
IS_STREAM = is_enabled('IS_STREAM', True)
VERIFY_EXPIRE = int(environ.get('VERIFY_EXPIRE', '86400'))
