import motor.motor_asyncio # Changed from pymongo.MongoClient
from info import ADMINS, DATABASE_NAME, DATA_DATABASE_URL, FILES_DATABASE_URL, SECOND_FILES_DATABASE_URL, IMDB_TEMPLATE, WELCOME_TEXT, LINK_MODE, TUTORIAL, SHORTLINK_URL, SHORTLINK_API, SHORTLINK, FILE_CAPTION, IMDB, WELCOME, SPELL_CHECK, PROTECT_CONTENT, AUTO_FILTER, AUTO_DELETE, IS_STREAM, VERIFY_EXPIRE
import time
from datetime import datetime, timedelta # Import timedelta for expiration calculation

# Changed to motor.motor_asyncio for asynchronous operations
files_db_client = motor.motor_asyncio.AsyncIOMotorClient(FILES_DATABASE_URL)
files_db = files_db_client[DATABASE_NAME]

data_db_client = motor.motor_asyncio.AsyncIOMotorClient(DATA_DATABASE_URL)
data_db = data_db_client[DATABASE_NAME]

if SECOND_FILES_DATABASE_URL:
     second_files_db_client = motor.motor_asyncio.AsyncIOMotorClient(SECOND_FILES_DATABASE_URL)
     second_files_db = second_files_db_client[DATABASE_NAME]

class Database:
    default_setgs = {
        'auto_filter': AUTO_FILTER,
        'file_secure': PROTECT_CONTENT,
        'imdb': IMDB,
        'spell_check': SPELL_CHECK,
        'auto_delete': AUTO_DELETE,
        'welcome': WELCOME,
        'welcome_text': WELCOME_TEXT,
        'template': IMDB_TEMPLATE,
        'caption': FILE_CAPTION,
        'url': SHORTLINK_URL,
        'api': SHORTLINK_API,
        'shortlink': SHORTLINK,
        'tutorial': TUTORIAL,
        'links': LINK_MODE
    }

    default_verify = {
        'is_verified': False,
        'verified_time': 0, # Stored as timestamp
        'verify_token': "",
        'link': "",
        'expire_time': 0 # Stored as timestamp
    }
    
    default_prm = {
        'expire': '',
        'trial': False,
        'plan': '',
        'premium': False
    }

    def __init__(self):
        self.col = data_db.Users
        self.grp = data_db.Groups
        self.prm = data_db.Premiums
        self.req = data_db.Requests
        self.con = data_db.Connections
        self.stg = data_db.Settings

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            verify_status=self.default_verify
        )

    def new_group(self, id, title):
        return dict(
            id = id,
            title = title,
            chat_status=dict(
                is_disabled=False,
                reason="",
            ),
            settings=self.default_setgs
        )
    
    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user) # Await the operation
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)}) # Await the operation
        return bool(user)
    
    async def total_users_count(self):
        count = await self.col.count_documents({}) # Await the operation
        return count
    
    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}}) # Await the operation
    
    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}}) # Await the operation

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)}) # Await the operation
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({}) # Returns an AsyncIOMotorCursor
    
    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)}) # Await the operation

    async def delete_chat(self, grp_id):
        await self.grp.delete_many({'id': int(grp_id)}) # Await the operation

    async def find_join_req(self, id): # Made async
        return bool(await self.req.find_one({'id': id})) # Await the operation

    async def add_join_req(self, id): # Made async
        await self.req.insert_one({'id': id}) # Await the operation

    async def del_join_req(self): # Made async
        await self.req.drop() # Await the operation

    async def get_banned(self):
        users_cursor = self.col.find({'ban_status.is_banned': True})
        chats_cursor = self.grp.find({'chat_status.is_disabled': True})
        
        b_chats = [chat['id'] async for chat in chats_cursor] # Iterate asynchronously
        b_users = [user['id'] async for user in users_cursor] # Iterate asynchronously
        return b_users, b_chats
    
    async def add_chat(self, chat_id, title): # Renamed 'chat' to 'chat_id' for clarity
        group_doc = self.new_group(chat_id, title)
        await self.grp.insert_one(group_doc) # Await the operation

    async def get_chat(self, chat_id): # Renamed 'chat' to 'chat_id' for clarity
        chat = await self.grp.find_one({'id':int(chat_id)}) # Await the operation
        return False if not chat else chat.get('chat_status')
    
    async def re_enable_chat(self, id):
        chat_status=dict(
            is_disabled=False,
            reason="",
            )
        await self.grp.update_one({'id': int(id)}, {'$set': {'chat_status': chat_status}}) # Await the operation
        
    async def update_settings(self, id, settings):
        await self.grp.update_one({'id': int(id)}, {'$set': {'settings': settings}}) # Await the operation     
    
    async def get_settings(self, id):
        chat = await self.grp.find_one({'id':int(id)}) # Await the operation
        if chat:
            return chat.get('settings', self.default_setgs)
        return self.default_setgs
    
    async def disable_chat(self, chat_id, reason="No Reason"): # Renamed 'chat' to 'chat_id' for clarity
        chat_status=dict(
            is_disabled=True,
            reason=reason,
            )
        await self.grp.update_one({'id': int(chat_id)}, {'$set': {'chat_status': chat_status}}) # Await the operation
    
    async def get_verify_status(self, user_id):
        user = await self.col.find_one({'id':int(user_id)}) # Await the operation
        if user:
            info = user.get('verify_status', self.default_verify)
            # Ensure expire_time is correctly calculated and updated if missing or based on old logic
            # This handles cases where 'expire_time' might not exist or needs re-calculation
            if 'expire_time' not in info or info['expire_time'] == 0:
                if info.get('verified_time'):
                    # verified_time is a timestamp, add VERIFY_EXPIRE seconds
                    info['expire_time'] = info['verified_time'] + VERIFY_EXPIRE
                    # Optionally, persist this back to the DB immediately for consistency
                    await self.col.update_one({'id': int(user_id)}, {'$set': {'verify_status.expire_time': info['expire_time']}})
            return info
        return self.default_verify
        
    async def update_verify_status(self, user_id, verify):
        await self.col.update_one({'id': int(user_id)}, {'$set': {'verify_status': verify}}) # Await the operation
    
    async def total_chat_count(self):
        count = await self.grp.count_documents({}) # Await the operation
        return count
    
    async def get_all_chats(self):
        return self.grp.find({}) # Returns an AsyncIOMotorCursor
    
    async def get_files_db_size(self):
        # Ensure these are awaited for motor clients
        return (await files_db.command("dbstats"))['dataSize']
   
    async def get_second_files_db_size(self):
        # Ensure these are awaited for motor clients
        if SECOND_FILES_DATABASE_URL: # Only attempt if second DB exists
            return (await second_files_db.command("dbstats"))['dataSize']
        return 0 # Return 0 if second DB not configured
    
    async def get_data_db_size(self):
        return (await data_db.command("dbstats"))['dataSize']
    
    async def get_all_chats_count(self):
        grp_count = await self.grp.count_documents({}) # Await the operation
        return grp_count
    
    async def get_plan(self, id): # Made async
        st = await self.prm.find_one({'id': id}) # Await the operation
        if st:
            return st['status']
        return self.default_prm
    
    async def update_plan(self, id, data): # Made async
        # Use upsert=True to insert if not found, otherwise update
        await self.prm.update_one({'id': id}, {'$set': {'status': data}}, upsert=True) # Await the operation

    async def get_premium_count(self): # Made async
        return await self.prm.count_documents({'status.premium': True}) # Await the operation
    
    async def get_premium_users(self): # Made async
        return self.prm.find({'status.premium': True}) # Returns an AsyncIOMotorCursor
    
    async def add_connect(self, group_id, user_id): # Made async
        # Use $addToSet to prevent duplicate group_ids in the array
        await self.con.update_one(
            {'_id': user_id},
            {"$addToSet": {"group_ids": group_id}},
            upsert=True # Creates the document if it doesn't exist
        )

    async def get_connections(self, user_id): # Made async
        user = await self.con.find_one({'_id': user_id}) # Await the operation
        if user:
            return user.get("group_ids", []) # Use .get with default for safety
        else:
            return []
        
    async def update_bot_sttgs(self, var, val): # Made async
        await self.stg.update_one({'id': 'settings'}, {'$set': {var: val}}, upsert=True) # Await the operation, use upsert
        
    async def get_bot_sttgs(self): # Made async
        return await self.stg.find_one({'id': 'settings'}) # Await the operation


db = Database()
