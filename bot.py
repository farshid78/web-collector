from telethon import TelegramClient
from telethon.errors import FloodWaitError
import os
import asyncio
import requests
import sys
import time

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

USERS_FILE = "users.txt"
FILE_DELAY = 1   # توقف بین ارسال هر فایل (برای جلوگیری از FloodWait)


def update_users():
    print("Fetching users from getUpdates...")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        resp = requests.get(url).json()
        ids = []

        if resp.get("ok"):
            for update in resp["result"]:
                if "message" in update:
                    ids.append(str(update["message"]["chat"]["id"]))

        # اضافه کردن کاربران قبلی
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE) as f:
                ids.extend(f.read().splitlines())

        # حذف تکراری‌ها
        ids = sorted(set(ids))

        # ذخیره
        with open(USERS_FILE, "w") as f:
            f.write("\n".join(ids))

        print("Users updated:", ids)

        # پاک کردن آپدیت‌های مصرف‌شده
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")

    except Exception as e:
        print("Error updating users:", e)


def get_all_config_files():
    """تمام فایل‌های configs_*.txt + configs.txt را پیدا می‌کند."""
    files = []

    for f in os.listdir("."):
        if f.startswith("configs") and f.endswith(".txt"):
            files.append(f)

    return sorted(files)


async def main():
    start_time = time.time()

    print("Starting bot...")

    update_users()

    client = TelegramClient("bot_session", API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    # بررسی users.txt
    if not os.path.exists(USERS_FILE):
        print("❌ users.txt پیدا نشد!")
        return

    with open(USERS_FILE) as f:
        users = [line.strip() for line in f if line.strip()]

    print("Users loaded:", users)

    # پیدا کردن همه فایل‌های configs_*.txt
    config_files = get_all_config_files()

    if not config_files:
        print("❌ هیچ فایل کانفیگی پیدا نشد!")
        print("محتویات پوشه:", os.listdir("."))
        return

    print("Found config files:", config_files)

    # آمار
    stats = {
        "total_users": len(users),
        "files_sent": 0,
        "messages": 0,
        "errors": 0,
    }

    # ارسال به همه کاربران (بدون Batch)
    for user in users:
        try:
            uid = int(user)
            print(f"\nSending to {uid}...")

            await client.send_message(uid, "آپدیت جدید کانفیگ‌ها آماده شد ✔")
            stats["messages"] += 1

            # ارسال همه فایل‌ها
            for file in config_files:
                print(f"Sending file {file} to {uid}")
                await client.send_file(uid, file)
                stats["files_sent"] += 1
                await asyncio.sleep(FILE_DELAY)

        except FloodWaitError as e:
            print(f"FloodWait → {e.seconds} ثانیه صبر می‌کنیم")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            print("❌ Error sending to", user, e)
            stats["errors"] += 1

    # گزارش نهایی
    duration = round(time.time() - start_time, 2)

    print("\n====================")
    print("📊 REPORT")
    print("====================")
    print(f"👥 Total users: {stats['total_users']}")
    print(f"📄 Total files sent: {stats['files_sent']}")
    print(f"💬 Total messages sent: {stats['messages']}")
    print(f"❌ Errors: {stats['errors']}")
    print(f"⏱ Duration: {duration} seconds")
    print("====================\n")

    await client.disconnect()
    sys.exit(0)


asyncio.run(main())
