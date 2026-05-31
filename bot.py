from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import asyncio
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

USERS_FILE = "users.txt"
FINAL_FILE = "config.txt"   # فایل کانفیگ در ریشه پروژه


async def main():
    print("Starting bot...")

    client = TelegramClient("bot_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    # چک فایل کاربران
    if not os.path.exists(USERS_FILE):
        print("❌ users.txt پیدا نشد!")
        return

    with open(USERS_FILE) as f:
        users = [line.strip() for line in f.readlines() if line.strip()]

    print("Users loaded:", users)

    if not users:
        print("❌ هیچ کاربری داخل users.txt نیست!")
        return

    # چک فایل کانفیگ
    if not os.path.exists(FINAL_FILE):
        print(f"❌ فایل {FINAL_FILE} پیدا نشد!")
        print("محتویات پوشه:", os.listdir("."))
        return

    print("Found config.txt, sending to users...")

    # ارسال برای همه
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
