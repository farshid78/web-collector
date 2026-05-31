from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os
import asyncio
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = TelegramClient(StringSession(""), API_ID, API_HASH)

USERS_FILE = "users.txt"

# -----------------------------
# ذخیره آیدی عددی کاربران
# -----------------------------
def add_user(user_id):
    user_id = str(user_id)

    # اگر فایل وجود نداشت → بساز
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(user_id + "\n")
        return

    # اگر وجود داشت → فقط اگر جدید بود اضافه کن
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()

    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(user_id + "\n")

# -----------------------------
# ثبت کاربر با /start
# -----------------------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_id = event.sender_id
    add_user(user_id)

    await event.respond("سلام! شما با موفقیت ثبت شدید ✔")

# -----------------------------
# ارسال فایل‌ها به همه کاربران
# -----------------------------
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

    await client.disconnect()
    sys.exit(0)

client.start()
client.loop.run_until_complete(main())
