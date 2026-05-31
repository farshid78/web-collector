from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
import os
import asyncio
import requests

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MODE = os.getenv("MODE", "LISTEN")  # LISTEN یا SEND

USERS_FILE = "users.txt"
FINAL_FILE = "configs_final.txt"

client = TelegramClient(StringSession(""), API_ID, API_HASH)


# -----------------------------
# ذخیره کاربر جدید
# -----------------------------
def add_user(user_id: int):
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


# -----------------------------
# حالت LISTEN → ثبت کاربران
# -----------------------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_id = event.sender_id
    add_user(user_id)
    await event.respond("سلام! شما با موفقیت ثبت شدید ✔")


@client.on(events.NewMessage)
async def any_message(event):
    user_id = event.sender_id
    add_user(user_id)


# -----------------------------
# حالت SEND → ارسال فایل‌ها
# -----------------------------
async def send_updates():
    await client.start(bot_token=BOT_TOKEN)

    # گرفتن کاربران از getUpdates
    fetch_updates()

    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            users = [line.strip() for line in f.readlines()]
    else:
        users = []

    if not os.path.exists(FINAL_FILE):
        print("configs_final.txt پیدا نشد!")
        return

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


# -----------------------------
# اجرای اصلی
# -----------------------------
if __name__ == "__main__":
    if MODE == "SEND":
        asyncio.run(send_updates())
    else:
        client.start(bot_token=BOT_TOKEN)
        client.run_until_disconnected()
