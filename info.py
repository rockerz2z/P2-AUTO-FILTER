import re
from os import environ
import os
from Script import script # Assuming Script.py is structured to be imported this way
import logging

logger = logging.getLogger(__name__)

def is_enabled(type, value):
    data = environ.get(type, str(value))
    if data.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif data.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        logger.error(f'Environment variable {type} has an invalid value: "{data}". Exiting now.')
        exit()

def is_valid_ip(ip):
    # Regex for IPv4 validation
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(ip_pattern, ip) is not None

# Bot information
API_ID = environ.get('API_ID', '21388641') # Kept original default
if not API_ID or not API_ID.isdigit():
    logger.error('API_ID is missing or invalid, exiting now')
    exit()
else:
    API_ID = int(API_ID)

API_HASH = environ.get('API_HASH', '16f909bd213b2222a620d7641036834e') # Kept original default
if not API_HASH:
    logger.error('API_HASH is missing, exiting now')
    exit()

BOT_TOKEN = environ.get('BOT_TOKEN', '7597832356:AAGpQHjrnv27rf9RN-Qk6vB2iF7auX4gq-0') # Kept original default
if not BOT_TOKEN:
    logger.error('BOT_TOKEN is missing, exiting now')
    exit()

PORT = int(environ.get('PORT', '8080')) # Kept original default

# Upload your images to "postimages.org" and get direct link
# Filter out empty strings that might result from .split() if env var is empty
PICS_RAW = environ.get('PICS', 'https://te.legra.ph/file/00c2b881ab6dd8680b232.jpg') # Use a temporary variable for raw string
PICS = [pic for pic in PICS_RAW.split() if pic.strip()] # Filter empty strings
if not PICS:
    logger.info('PICS environment variable is empty or not set. Using a default placeholder if available or handling in code.')
    # If PICS is critical and no default is provided via env, you might want to exit or use a hardcoded fallback
    # For now, it will be an empty list if the env var is empty.

# Bot Admins
# Filter out empty strings and convert to int
ADMINS_RAW = environ.get('ADMINS', '1078638766 6221939103') # Use a temporary variable for raw string
ADMINS = [int(admin) for admin in ADMINS_RAW.split() if admin.strip().isdigit()]
if not ADMINS:
    logger.error('ADMINS is missing or invalid, exiting now. Please provide at least one valid admin ID.')
    exit()

# Channels
# Filter out empty strings and convert to int, handling potential usernames (non-int)
INDEX_CHANNELS_RAW = environ.get('INDEX_CHANNELS', '-1001660466640 -1001505006734') # Use a temporary variable for raw string
INDEX_CHANNELS = [
    int(channel) if (channel.startswith("-100") and channel[1:].isdigit()) or channel.isdigit() else channel
    for channel in INDEX_CHANNELS_RAW.split() if channel.strip()
]
if not INDEX_CHANNELS:
    logger.info('INDEX_CHANNELS is empty or not set. No channels will be indexed automatically.')

LOG_CHANNEL = environ.get('LOG_CHANNEL', '-1002280301241') # Kept original default
if not LOG_CHANNEL or (not str(LOG_CHANNEL).startswith("-100") and not str(LOG_CHANNEL).isdigit()):
    logger.error('LOG_CHANNEL is missing or invalid, exiting now. Must be a valid channel ID (e.g., -100xxxxxxxxxx).')
    exit()
else:
    LOG_CHANNEL = int(LOG_CHANNEL)
    
# support group
SUPPORT_GROUP = environ.get('SUPPORT_GROUP', '-1002481606158') # Kept original default
if not SUPPORT_GROUP or (not str(SUPPORT_GROUP).startswith("-100") and not str(SUPPORT_GROUP).isdigit()):
    logger.error('SUPPORT_GROUP is missing or invalid, exiting now. Must be a valid group ID (e.g., -100xxxxxxxxxx).')
    exit()
else:
    SUPPORT_GROUP = int(SUPPORT_GROUP)

# MongoDB information
DATA_DATABASE_URL = environ.get('DATA_DATABASE_URL', "mongodb+srv://riyazahamed1806:Riyazkk2003@cluster0.emcu0y2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # Kept original default
if not DATA_DATABASE_URL:
    logger.error('DATA_DATABASE_URL is missing, exiting now')
    exit()

FILES_DATABASE_URL = environ.get('FILES_DATABASE_URL', "mongodb+srv://riyazahamed1806:Riyazkk2003@cluster0.q2whrny.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # Kept original default
if not FILES_DATABASE_URL:
    logger.error('FILES_DATABASE_URL is missing, exiting now')
    exit()

SECOND_FILES_DATABASE_URL = environ.get('SECOND_FILES_DATABASE_URL', "mongodb+srv://riyazahamed1806:Riyazkk2003@cluster0.v0ovwye.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") # Kept original default
if not SECOND_FILES_DATABASE_URL:
    logger.info('SECOND_FILES_DATABASE_URL is empty or not set. Only primary files database will be used.')

DATABASE_NAME = environ.get('DATABASE_NAME', "Riyaz18") # Kept original default
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Files') # Kept original default

# Links
SUPPORT_LINK = environ.get('SUPPORT_LINK', 'https://t.me/R2K_Support') # Kept original default
UPDATES_LINK = environ.get('UPDATES_LINK', 'https://t.me/Rockerz2z') # Kept original default
FILMS_LINK = environ.get('FILMS_LINK', 'https://t.me/+ANbMXPyGtZxmZjg1') # Kept original default # Movie Request Group link
TUTORIAL = environ.get("TUTORIAL", "https://t.me/HOWTODOWNLOAD25") # Kept original default
VERIFY_TUTORIAL = environ.get("VERIFY_TUTORIAL", "https://t.me/HOWTODOWNLOAD25") # Kept original default

# Bot settings
DELETE_TIME = int(environ.get('DELETE_TIME', 3600)) # Kept original default # Add time in seconds
CACHE_TIME = int(environ.get('CACHE_TIME', 300)) # Kept original default
MAX_BTN = int(environ.get('MAX_BTN', 8)) # Kept original default
LANGUAGES_RAW = environ.get('LANGUAGES', 'hindi english telugu tamil kannada malayalam marathi punjabi') # Use temporary variable
LANGUAGES = [lang.lower() for lang in LANGUAGES_RAW.split() if lang.strip()] # Filter empty strings
QUALITY_RAW = environ.get('QUALITY', '360p 480p 720p 1080p 2160p') # Use temporary variable
QUALITY = [q.lower() for q in QUALITY_RAW.split() if q.strip()] # Filter empty strings

# These might be defined in Script.py, ensure Script is imported correctly
# and these variables exist in the script object
IMDB_TEMPLATE = environ.get("IMDB_TEMPLATE", getattr(script, 'IMDB_TEMPLATE', ''))
FILE_CAPTION = environ.get("FILE_CAPTION", getattr(script, 'FILE_CAPTION', ''))
WELCOME_TEXT = environ.get("WELCOME_TEXT", getattr(script, 'WELCOME_TEXT', ''))

SHORTLINK_URL = environ.get("SHORTLINK_URL", "linkcents.com") # Kept original default
SHORTLINK_API = environ.get("SHORTLINK_API", "602dc472c97f6d6055bae9f35fa81f79009f4a7f") # Kept original default
VERIFY_EXPIRE = int(environ.get('VERIFY_EXPIRE', 86400)) # Kept original default # Add time in seconds
INDEX_EXTENSIONS_RAW = environ.get('INDEX_EXTENSIONS', 'mp4 mkv') # Use temporary variable
INDEX_EXTENSIONS = [ext.lower() for ext in INDEX_EXTENSIONS_RAW.split() if ext.strip()] # Filter empty strings
PM_FILE_DELETE_TIME = int(environ.get('PM_FILE_DELETE_TIME', '3600')) # Kept original default

# boolean settings
USE_CAPTION_FILTER = is_enabled('USE_CAPTION_FILTER', False) # Kept original default
IS_VERIFY = is_enabled('IS_VERIFY', False) # Kept original default
AUTO_DELETE = is_enabled('AUTO_DELETE', True) # Kept original default
WELCOME = is_enabled('WELCOME', False) # Kept original default
PROTECT_CONTENT = is_enabled('PROTECT_CONTENT', False) # Kept original default
LONG_IMDB_DESCRIPTION = is_enabled("LONG_IMDB_DESCRIPTION", False) # Kept original default
LINK_MODE = is_enabled("LINK_MODE", True) # Kept original default
AUTO_FILTER = is_enabled('AUTO_FILTER', True) # Kept original default
IMDB = is_enabled('IMDB', False) # Kept original default
SPELL_CHECK = is_enabled("SPELL_CHECK", True) # Kept original default
SHORTLINK = is_enabled('SHORTLINK', True) # Kept original default
PM_SEARCH = is_enabled('PM_SEARCH', True) # Kept original default

# for stream
IS_STREAM = is_enabled('IS_STREAM', False) # Kept original default
BIN_CHANNEL = environ.get("BIN_CHANNEL", "-1002411870433") # Kept original default
if not BIN_CHANNEL or (not str(BIN_CHANNEL).startswith("-100") and not str(BIN_CHANNEL).isdigit()):
    logger.error('BIN_CHANNEL is missing or invalid, exiting now. Must be a valid channel ID (e.g., -100xxxxxxxxxx).')
    exit()
else:
    BIN_CHANNEL = int(BIN_CHANNEL)

URL = environ.get("URL", "https://onlinewatch.koyeb.app/") # Kept original default
if not URL:
    logger.error('URL is missing, exiting now')
    exit()
else:
    if URL.startswith(('https://', 'http://')):
        if not URL.endswith("/"):
            URL += '/'
    elif is_valid_ip(URL):
        URL = f'http://{URL}/'
    else:
        logger.error(f'URL "{URL}" is not valid, exiting now. Must be a valid URL or IP address.')
        exit()

#start command reactions and sticker
REACTIONS_RAW = environ.get('REACTIONS', '🤝 😇 🤗 😍 👍 🎅 😐 🥰 🤩 😱 🤣 😘 👏 😛 😈 🎉 ⚡️ 🫡 🤓 😎 🏆 🔥 🤭 🌚 🆒 👻 😁') # Use temporary variable
REACTIONS = [r for r in REACTIONS_RAW.split() if r.strip()] # Filter empty strings
STICKERS_RAW = environ.get('STICKERS', 'CAACAgUAAxkBAAELTeJoJHtQsLxJJfkT4JakLxbUjcKz8wACjwIAAsnn6FVsAf5eBhi7Sh4E') # Use temporary variable
STICKERS = [s for s in STICKERS_RAW.split() if s.strip()] # Filter empty strings


# for Premium 
IS_PREMIUM = is_enabled('IS_PREMIUM', False) # Kept original default
PRE_DAY_AMOUNT = int(environ.get('PRE_DAY_AMOUNT', '10')) # Kept original default # add amount in INR for premium charge pre day 
UPI_ID = environ.get("UPI_ID", "xyz") # Kept original default
UPI_NAME = environ.get("UPI_NAME", "zyz") # Kept original default # add your UPI account name

if not UPI_ID or not UPI_NAME:
    logger.info('UPI_ID or UPI_NAME is empty. IS_PREMIUM will be disabled.')
    IS_PREMIUM = False

RECEIPT_SEND_USERNAME = environ.get("RECEIPT_SEND_USERNAME", "@Hansaka_Anuhas") # Kept original default
