import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
import motor.motor_asyncio # Changed from pymongo.MongoClient
from pymongo import TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure
from info import USE_CAPTION_FILTER, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

logger = logging.getLogger(__name__)

# Changed to motor.motor_asyncio for asynchronous operations
client = motor.motor_asyncio.AsyncIOMotorClient(FILES_DATABASE_URL)
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

async def ensure_indexes(): # Made index creation async
    try:
        await collection.create_index([("file_name", TEXT)], background=True)
        await collection.create_index("file_id", unique=True, background=True) # Adding unique index for file_id (as _id)
        await collection.create_index("caption", background=True)
        await collection.create_index("chat_id", background=True) # Index for chat_id
    except OperationFailure as e:
        if 'quota' in str(e).lower():
            if not SECOND_FILES_DATABASE_URL:
                logger.error(f'your FILES_DATABASE_URL is already full, add SECOND_FILES_DATABASE_URL')
            else:
                logger.warning('Primary FILES_DATABASE_URL appears full, indexing might be limited. Attempting with SECOND_FILES_DATABASE_URL if available.')
        else:
            logger.exception(e)
    except Exception as e:
        logger.exception(f"Error ensuring indexes for primary DB: {e}")

# Call ensure_indexes at module load or bot startup, e.g., in your main app.py
# For now, it's defined here and can be called explicitly later.
# In a real bot, you'd typically call this when the bot starts up.
# For this file, I'll just keep the function definition, assuming it will be called.

if SECOND_FILES_DATABASE_URL:
    second_client = motor.motor_asyncio.AsyncIOMotorClient(SECOND_FILES_DATABASE_URL)
    second_db = second_client[DATABASE_NAME]
    second_collection = second_db[COLLECTION_NAME]
    async def ensure_second_indexes(): # Made index creation async for second DB
        try:
            await second_collection.create_index([("file_name", TEXT)], background=True)
            await second_collection.create_index("file_id", unique=True, background=True)
            await second_collection.create_index("caption", background=True)
            await second_collection.create_index("chat_id", background=True) # Index for chat_id
        except Exception as e:
            logger.exception(f"Error ensuring indexes for secondary DB: {e}")

# Functions to get counts
async def second_db_count_documents():
     if SECOND_FILES_DATABASE_URL:
        return await second_collection.count_documents({})
     return 0

async def db_count_documents():
     return await collection.count_documents({})


async def save_file(media):
    """Save file in database"""
    file_id = unpack_new_file_id(media.file_id)
    # Clean file name and caption for better searchability
    file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name or "")).strip()
    file_caption = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.caption or "")).strip()
    
    document = {
        '_id': file_id, # Using the unpacked file_id as _id
        'file_name': file_name,
        'file_size': media.file_size,
        'caption': file_caption,
        'chat_id': media.chat.id,    # Store chat_id
        'message_id': media.id,      # Store message_id
        'date': media.date.isoformat(), # Store date for potential sorting
        'mime_type': media.media.value if media.media else 'unknown' # Store media type (e.g., MessageMediaType.VIDEO.value)
    }
    
    try:
        await collection.insert_one(document) # Await the operation
        logger.info(f'Saved to primary DB - {file_name}')
        return 'suc'
    except DuplicateKeyError:
        logger.warning(f'Already Saved in primary DB - {file_name}')
        return 'dup'
    except OperationFailure as e:
        logger.error(f'OperationFailure in primary DB for {file_name}: {e}', exc_info=True)
        if 'quota' in str(e).lower() and SECOND_FILES_DATABASE_URL:
            logger.info('Primary FILES_DATABASE_URL appears full, trying SECOND_FILES_DATABASE_URL')
            try:
                await second_collection.insert_one(document) # Await the operation
                logger.info(f'Saved to 2nd db - {file_name}')
                return 'suc'
            except DuplicateKeyError:
                logger.warning(f'Already Saved in 2nd db - {file_name}')
                return 'dup'
            except Exception as e_2nd:
                logger.error(f'Error saving to 2nd db for {file_name}: {e_2nd}', exc_info=True)
                return 'err'
        else:
            logger.error(f'Unhandled OperationFailure for {file_name}: {e}', exc_info=True)
            return 'err'
    except Exception as e:
        logger.error(f'Unexpected error saving file {file_name}: {e}', exc_info=True)
        return 'err'


async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        # Use word boundaries for single word searches
        raw_pattern = r'\b' + re.escape(query) + r'\b'
    else:
        # For multiple words, use regex to match them with flexible separators
        raw_pattern = '.*'.join(re.escape(word) for word in query.split())
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logger.warning(f"Invalid regex query '{query}': {e}. Falling back to exact match for query.")
        regex = re.compile(re.escape(query), flags=re.IGNORECASE) # Fallback to safer regex

    if USE_CAPTION_FILTER:
        filter_query = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter_query = {'file_name': regex}

    primary_cursor = collection.find(filter_query)
    results = await primary_cursor.to_list(length=None) # Await and get all results

    if SECOND_FILES_DATABASE_URL:
        second_cursor = second_collection.find(filter_query)
        results.extend(await second_cursor.to_list(length=None)) # Await and extend

    # Sort results by relevance or date if needed. For now, just order as found.
    # It's good practice to sort for consistent paging. Let's sort by file_name.
    results.sort(key=lambda x: x.get('file_name', '').lower())

    if lang:
        # Filter by language, assuming lang is part of file_name (e.g., [telugu], [eng])
        lang_files = [file for file in results if lang.lower() in file.get('file_name', '').lower()]
        files = lang_files[offset:offset + max_results]
        total_results = len(lang_files)
    else:
        files = results[offset:offset + max_results]
        total_results = len(results)

    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''

    return files, next_offset, total_results

async def delete_files(query):
    query = query.strip()
    if not query:
        # If query is empty, delete nothing or handle as "delete all" (dangerous)
        # Assuming it means delete nothing if query is empty based on original behavior.
        return 0
    elif ' ' not in query:
        raw_pattern = r'\b' + re.escape(query) + r'\b'
    else:
        raw_pattern = '.*'.join(re.escape(word) for word in query.split())
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception as e:
        logger.warning(f"Invalid regex for delete query '{query}': {e}. Falling back to exact match.")
        regex = re.compile(re.escape(query), flags=re.IGNORECASE)
        
    filter_query = {'file_name': regex}
    
    result1 = await collection.delete_many(filter_query) # Await the operation
    total_deleted = result1.deleted_count
    
    result2 = None
    if SECOND_FILES_DATABASE_URL:
        result2 = await second_collection.delete_many(filter_query) # Await the operation
        total_deleted += result2.deleted_count
    
    return total_deleted

async def get_file_details(query):
    file_details = await collection.find_one({'_id': query}) # Await the operation
    if not file_details and SECOND_FILES_DATABASE_URL:
        file_details = await second_collection.find_one({'_id': query}) # Await the operation
    return file_details

def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id
