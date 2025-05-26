import math
from typing import Union
from pyrogram.types import Message
from utils import temp
from pyrogram import Client, utils, raw
from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid
from pyrogram.file_id import FileId, FileType, ThumbnailSource


async def chunk_size(length):
    return 2 ** max(min(math.ceil(math.log2(length / 1024)), 10), 2) * 1024


async def offset_fix(offset, chunksize):
    offset -= offset % chunksize
    return offset


class TGCustomYield:
    def __init__(self):
        """ A custom method to stream files from telegram.
        functions:
            generate_file_properties: returns the properties for a media on a specific message contained in FileId class.
            generate_media_session: returns the media session for the DC that contains the media file on the message.
            yield_file: yield a file from telegram servers for streaming.
        """
        self.main_bot = temp.BOT

    @staticmethod
    async def generate_file_properties(msg: Message):
        media = getattr(msg, msg.media.value, None)
        file_id_obj = FileId.decode(media.file_id)
        return file_id_obj

    async def generate_media_session(self, client: Client, msg: Message):
        data = await self.generate_file_properties(msg)

        media_session = client.media_sessions.get(data.dc_id, None)

        if media_session is None:
            if data.dc_id == utils.get_peer_id(client.me.id):
                media_session = client.delegate_session
            else:
                media_session = Session(
                    client, data.dc_id, await Auth(client, data.dc_id).create()
                )
            client.media_sessions[data.dc_id] = media_session
        return media_session

    async def get_location(self, data: FileId):
        if data.file_type == FileType.DOCUMENT:
            return raw.types.InputDocumentFileLocation(
                id=data.media_id,
                access_hash=data.access_hash,
                file_reference=data.file_reference,
                thumb_size=""
            )
        elif data.file_type == FileType.PHOTO:
            return raw.types.InputPhotoFileLocation(
                id=data.media_id,
                access_hash=data.access_hash,
                file_reference=data.file_reference,
                thumb_size=""
            )
        elif data.file_type == FileType.WEB_DOCUMENT:
            if data.url.startswith("http"):
                return raw.types.InputWebFileLocation(
                    url=data.url,
                    access_hash=data.access_hash
                )
        else:
            raise Exception("Unsupported file type")

    async def yield_file(self, media_msg: Message):
        client = self.main_bot
        data = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)

        location = await self.get_location(data)

        if data.file_type == FileType.WEB_DOCUMENT:
            r = await media_session.send(
                raw.functions.upload.GetWebFile(
                    location=location,
                    offset=0,
                    limit=1024 * 1024
                ),
            )
            yield r.bytes
            return

        offset = 0
        chunk_s = await chunk_size(data.file_size)
        
        while True:
            try:
                r = await media_session.send(
                    raw.functions.upload.GetFile(
                        location=location,
                        offset=offset,
                        limit=chunk_s
                    ),
                )
            except AuthBytesInvalid:
                await media_session.recreate()
                continue
            except Exception as e:
                # Log the error, but don't stop the stream if it's recoverable
                print(f"Error fetching file chunk: {e}")
                break

            if isinstance(r, raw.types.upload.File):
                if r.bytes:
                    yield r.bytes
                    offset += chunk_s
                else:
                    break
            else:
                break

    async def download_as_bytesio(self, media_msg: Message):
        client = self.main_bot
        data = await self.generate_file_properties(media_msg)
        media_session = await self.generate_media_session(client, media_msg)

        location = await self.get_location(data)

        limit = 1024 * 1024
        offset = 0

        r = await media_session.send(
            raw.functions.upload.GetFile(
                location=location,
                offset=offset,
                limit=limit
            )
        )

        if isinstance(r, raw.types.upload.File):
            m_file = []
            # m_file.name = file_name
            while True:
                chunk = r.bytes

                if not chunk:
                    break

                m_file.append(chunk)

                offset += limit

                r = await media_session.send(
                    raw.functions.upload.GetFile(
                        location=location,
                        offset=offset,
                        limit=limit
                    )
                )

            return m_file
