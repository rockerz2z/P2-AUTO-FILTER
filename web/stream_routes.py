import math
import secrets
import mimetypes
import logging
from info import BIN_CHANNEL
from utils import temp
from aiohttp import web
from web.utils.custom_dl import TGCustomYield, chunk_size, offset_fix
from web.utils.render_template import media_watch
from pyrogram.errors import MessageIdInvalid, FloodWait, RPCError

# Configure logging (you might want to move this to a central logging setup)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text='<h1 align=\"center\"><a href=\"https://t.me/HA_Bots\"><b>HA Bots</b></a></h1>', content_type='text/html')


@routes.get("/watch/{message_id}")
async def watch_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        html_content = await media_watch(message_id)
        if "Error:" in html_content or "An error occurred" in html_content:
            logger.error(f"Error rendering watch page for message ID {message_id}: {html_content}")
            return web.Response(text=html_content, content_type='text/html', status=500)
        return web.Response(text=html_content, content_type='text/html')
    except ValueError:
        logger.warning(f"Invalid message_id received for watch_handler: {request.match_info['message_id']}")
        return web.Response(text="<h1>Bad Request: Invalid Message ID format.</h1>", content_type='text/html', status=400)
    except MessageIdInvalid:
        logger.warning(f"Message ID {request.match_info['message_id']} not found or invalid.")
        return web.Response(text="<h1>Not Found: Media not found.</h1>", content_type='text/html', status=404)
    except Exception as e:
        logger.exception(f"Unhandled error in watch_handler for message ID {request.match_info['message_id']}: {e}")
        return web.Response(text="<h1>Internal Server Error: Something went wrong.</h1>", content_type='text/html', status=500)
        

@routes.get("/download/{message_id}")
async def download_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return await media_download(request, message_id)
    except ValueError:
        logger.warning(f"Invalid message_id received for download_handler: {request.match_info['message_id']}")
        return web.Response(text="<h1>Bad Request: Invalid Message ID format.</h1>", content_type='text/html', status=400)
    except (MessageIdInvalid, AttributeError): # AttributeError can occur if media is None or its properties are missing
        logger.warning(f"Media not found or invalid for message ID {request.match_info['message_id']}.")
        return web.Response(text="<h1>Not Found: Media not found or inaccessible.</h1>", content_type='text/html', status=404)
    except FloodWait as e:
        logger.warning(f"FloodWait error for message ID {request.match_info['message_id']}: {e.value} seconds.")
        return web.Response(text=f"<h1>Too Many Requests: Please try again after {e.value} seconds.</h1>", content_type='text/html', status=429)
    except RPCError as e:
        logger.error(f"Telegram RPC error for message ID {request.match_info['message_id']}: {e}")
        return web.Response(text="<h1>Internal Server Error: Telegram API error.</h1>", content_type='text/html', status=500)
    except Exception as e:
        logger.exception(f"Unhandled error in download_handler for message ID {request.match_info['message_id']}: {e}")
        return web.Response(text="<h1>Internal Server Error: Something went wrong during download.</h1>", content_type='text/html', status=500)
        

async def media_download(request, message_id: int):
    range_header = request.headers.get('Range', 0)
    media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
    
    # Ensure media_msg has media and required attributes
    if not media_msg or not media_msg.media:
        raise MessageIdInvalid("Message does not contain media or message ID is invalid.")
        
    media = getattr(media_msg, media_msg.media.value, None)

    if not media or not hasattr(media, 'file_size') or not hasattr(media, 'file_name') or not hasattr(media, 'mime_type'):
        raise AttributeError("Media object is incomplete or missing required attributes.")

    file_size = media.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = request.http_range.stop or file_size - 1

    req_length = until_bytes - from_bytes

    new_chunk_size = await chunk_size(req_length)
    offset = await offset_fix(from_bytes, new_chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = (until_bytes % new_chunk_size) + 1
    part_count = math.ceil(req_length / new_chunk_size)
    body = TGCustomYield().yield_file(media_msg, offset, first_part_cut, last_part_cut, part_count, new_chunk_size)

    file_name = media.file_name if media.file_name else f"{secrets.token_hex(2)}.bin" # Default to .bin if no filename
    
    # Improved MIME type guessing
    mime_type = media.mime_type
    if not mime_type:
        guessed_mime = mimetypes.guess_type(file_name)[0]
        mime_type = guessed_mime if guessed_mime else "application/octet-stream" # Fallback to generic binary type


    headers = {
        "Content-Type": mime_type,
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"inline; filename=\"{file_name}\""
    }

    status_code = 200
    if range_header:
        status_code = 206
        headers["Content-Range"] = f"bytes {from_bytes}-{until_bytes}/{file_size}"
        headers["Content-Length"] = str(req_length + 1) # +1 because range is inclusive
    else:
        headers["Content-Length"] = str(file_size)

    return web.Response(
        status=status_code,
        body=body,
        headers=headers
    )
