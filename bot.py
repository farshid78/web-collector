from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import os
import asyncio
import requests
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")
MODE = os.getenv("MODE", "LISTEN")

USERS_FILE = "users.txt"
FINAL_FILE = "good_configs.txt"   # فایل خروجی تستر


# -----------------------------
# ذخیره کاربر جدید
# -----------------------------
def add_user(user_id):
    try:
        user_id = int(user_id)
        if user_id <= 0:
            return
    except:
        return

    user_id = str(user_id)

    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(user_id + "\n")
        return

    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()

    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(user_id + "\n")


# -----------------------------
# گرفتن آیدی‌ها از getUpdates
# -----------------------------
def fetch_updates():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url).json()
        if resp.get("ok"):
            for update in resp["result"]:
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    add_user(chat_id)
    except Exception as e:
        print("Error fetching updates:", e)


# ============================================================
# حالت LISTEN → با SESSION_STRING (اکانت شخصی)
# ============================================================
if MODE == "LISTEN":
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    @client.on(events.NewMessage(pattern="/start"))
    async def start(event):
        add_user(event.sender_id)
        await event.respond("سلام! شما با موفقیت ثبت شدید ✔")

    @client.on(events.NewMessage)
    async def any_message(event):
        add_user(event.sender_id)

    client.start()
    client.run_until_disconnected()


# ============================================================
# حالت SEND → ارسال خودکار با Bot Token
# ============================================================
else:
    client = TelegramClient("bot_session", API_ID, API_HASH)

    async def send_updates():
        await client.start(bot_token=BOT_TOKEN)

        # گرفتن آیدی‌ها از getUpdates
        fetch_updates()

        # خواندن لیست کاربران
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE) as f:
                users = [line.strip() for line in f.readlines()]
        else:
            users = []

        if not users:
            print("هیچ کاربری ثبت نشده!")
            return

        # فایل خروجی تستر
        if not os.path.exists(FINAL_FILE):
            print(f"{FINAL_FILE} پیدا نشد!")
            return

        # ارسال برای همه
        for user in users:
            try:
                uid = int(user)
                print(f"Sending to {uid}...")

                await client.send_message(uid, "آپدیت جدید آماده شد ✔")
                await client.send_file(uid, FINAL_FILE)

                await asyncio.sleep(1)

            except FloodWaitError as e:
                print(f"FloodWait → {e.seconds} ثانیه صبر می‌کنیم")
                await asyncio.sleep(e.seconds)

            except Exception as e:
                print("Error sending to", user, e)

        print("Done.")
        await client.disconnect()
        sys.exit(0)

    asyncio.run(send_updates())
