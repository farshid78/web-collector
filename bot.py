import os
import json
import asyncio
import requests
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

USERS_FILE = "users.json"


# -----------------------------
# مدیریت کاربران
# -----------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        save_users([])
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_users(users):
    users = list(dict.fromkeys(users))
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def get_users_from_telegram():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        return [
            update["message"]["from"]["id"]
            for update in r.json().get("result", [])
            if "message" in update
        ]
    except:
        return []


# -----------------------------
# دریافت فایل‌های کانفیگ
# -----------------------------
def get_config_files():
    files = []

    # فایل اصلی
    if os.path.exists("configs.txt"):
        files.append("configs.txt")

    # فایل‌های کشورها
    for f in sorted(os.listdir(".")):
        if f.startswith("configs_") and f.endswith(".txt"):
            files.append(f)

    print("📁 Files to send:", files)
    return files


# -----------------------------
# اجرای اصلی بات
# -----------------------------
async def main():
    print("🤖 BOT STARTED")

    client = TelegramClient("bot_session", API_ID, API_HASH)

    try:
        await client.start(bot_token=BOT_TOKEN)
        print("✅ Bot connected")
    except Exception as e:
        print("❌ Bot connection error:", e)
        return

    # بروزرسانی کاربران
    users = load_users()
    new_users = get_users_from_telegram()

    for uid in new_users:
        if uid not in users:
            users.append(uid)
            print(f"➕ New user added: {uid}")

    save_users(users)

    config_files = get_config_files()

    # ارسال به کاربران
    for idx, user_id in enumerate(users, 1):
        print(f"\n[{idx}/{len(users)}] Sending to {user_id}")

        try:
            # پیام اول
            await client.send_message(
                user_id,
                "🟢 **آپدیت جدید کانفیگ‌ها آماده شد**\n"
                "فایل‌ها بر اساس کشور دسته‌بندی شده‌اند:"
            )

            # ارسال همه فایل‌ها
            for file in config_files:
                print(f"   ↳ Sending {file}")
                await client.send_file(user_id, file)
                await asyncio.sleep(1.2)

            print(f"✅ Done for {user_id}")

        except FloodWaitError as e:
            print(f"⏳ FloodWait: {e.seconds} sec")
            await asyncio.sleep(e.seconds + 2)

        except Exception as e:
            print(f"❌ Error sending to {user_id}: {e}")

    # هندلر /start
    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        uid = event.sender_id
        if uid not in users:
            users.append(uid)
            save_users(users)
        await event.respond(
            "سلام! 👋\n"
            "از این به بعد هر ۱۰ دقیقه کانفیگ‌های جدید بر اساس کشور برات ارسال می‌شه."
        )

    await asyncio.sleep(30)
    await client.disconnect()
    print("🏁 BOT FINISHED")


if __name__ == "__main__":
    asyncio.run(main())
