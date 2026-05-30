from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 38225291  # اینجا API_ID خودت را بگذار
api_hash = "ed84535742ca8bb351441b5c77303254"  # اینجا API_HASH خودت را بگذار

# بدون پروکسی → مستقیم از اینترنت سیستم
proxy = None

with TelegramClient(StringSession(), api_id, api_hash, proxy=proxy) as client:
    print("SESSION_STRING:")
    print(client.session.save())

