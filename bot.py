from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient
from telethon.sessions import StringSession
import os
import asyncio
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = TelegramClient(StringSession(""), API_ID, API_HASH)

async def main():
    await client.start(bot_token=BOT_TOKEN)

    users = []
    if os.path.exists("users.txt"):
        with open("users.txt") as f:
            users = [line.strip() for line in f.readlines()]

    for user in users:
        try:
            await client.send_message(int(user), "آپدیت جدید آماده شد ✔")
            if os.path.exists("configs.txt"):
                await client.send_file(int(user), "configs.txt")
            if os.path.exists("results.txt"):
                await client.send_file(int(user), "results.txt")
        except Exception as e:
            print("Error sending to", user, e)

    print("Done.")

    # مهم: اتصال را ببند
    await client.disconnect()

    # مهم: برنامه را کامل ببند
    sys.exit(0)

asyncio.run(main())
