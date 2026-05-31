from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import asyncio
import requests
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

USERS_FILE = "users.txt"
FINAL_FILE = "configs.txt"


def update_users():
    print("Fetching users from getUpdates...")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url).json()
        ids = []

        if resp.get("ok"):
            for update in resp["result"]:
                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    ids.append(str(chat_id))

        if os.path.exists(USERS_FILE):
            with open(USERS_FILE) as f:
                old = f.read().splitlines()
                ids.extend(old)

        ids = sorted(set(ids))

        with open(USERS_FILE, "w") as f:
            f.write("\n".join(ids))

        print("Users updated:", ids)

        # پاک کردن آپدیت‌های مصرف‌شده
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
        except Exception:
            pass

    except Exception as e:
        print("Error updating users:", e)


async def main():
    print("Starting bot...")

    update_users()

    client = TelegramClient("bot_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    if not os.path.exists(USERS_FILE):
        print("❌ users.txt پیدا نشد!")
        return

    with open(USERS_FILE) as f:
        users = [line.strip() for line in f.readlines() if line.strip()]

    print("Users loaded:", users)

    if not users:
        print("❌ هیچ کاربری داخل users.txt نیست!")
        return

    if not os.path.exists(FINAL_FILE):
        print(f"❌ فایل {FINAL_FILE} پیدا نشد!")
        print("محتویات پوشه:", os.listdir("."))
        return

    print("Found configs.txt, sending to users...")

    for user in users:
        try:
            uid = int(user)
            print(f"Sending to {uid}...")

            await client.send_message(uid, "آپدیت جدید کانفیگ‌ها آماده شد ✔")
            await client.send_file(uid, FINAL_FILE)

            await asyncio.sleep(1)

        except FloodWaitError as e:
            print(f"FloodWait → {e.seconds} ثانیه صبر می‌کنیم")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print("❌ Error sending to", user, e)

    print("Done.")
    await client.disconnect()
    sys.exit(0)


asyncio.run(main())
