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

def load_users():
    if not os.path.exists(USERS_FILE):
        save_users([])
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            print(f"📋 Loaded {len(users)} users from users.json")
            return users
    except:
        return []

def save_users(users):
    try:
        # حذف تکراری‌ها
        unique_users = list(dict.fromkeys(users))
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(unique_users, f, indent=2)
        print(f"💾 Saved {len(unique_users)} users")
    except Exception as e:
        print(f"❌ Error saving users: {e}")

def get_users_from_telegram():
    """دریافت کاربران جدید از getUpdates"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"❌ getUpdates failed: {response.status_code}")
            return []

        data = response.json()
        new_users = []

        for update in data.get("result", []):
            if "message" in update:
                user_id = update["message"]["from"]["id"]
                new_users.append(user_id)

        print(f"🔄 Found {len(new_users)} recent users from getUpdates")
        return new_users

    except Exception as e:
        print(f"❌ Error in getUpdates: {e}")
        return []

def get_config_files():
    files = [f for f in os.listdir(".") if f.startswith("configs") and f.endswith(".txt")]
    print(f"📁 Found {len(files)} config files: {files}")
    return sorted(files)

async def main():
    print("🤖 BOT STARTED")

    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is missing!")
        return

    client = TelegramClient("bot_session", API_ID, API_HASH)

    try:
        await client.start(bot_token=BOT_TOKEN)
        print("✅ Bot connected successfully")
    except Exception as e:
        print(f"❌ Bot connection error: {e}")
        return

    # === بروزرسانی لیست کاربران ===
    users = load_users()
    telegram_users = get_users_from_telegram()

    # اضافه کردن کاربران جدید
    for uid in telegram_users:
        if uid not in users:
            users.append(uid)
            print(f"➕ New user added from getUpdates: {uid}")

    save_users(users)

    config_files = get_config_files()

    # === ارسال پیام به کاربران ===
    if users and config_files:
        print(f"📤 Sending configs to {len(users)} users...")
        for i, user_id in enumerate(users, 1):
            print(f"[{i}/{len(users)}] → User {user_id}")
            try:
                await client.send_message(user_id, "🟢 آپدیت جدید کانفیگ‌ها آماده شد!")
                
                for file in config_files:
                    await client.send_file(user_id, file)
                    await asyncio.sleep(1.3)
                
                print(f"✅ Sent to {user_id}")
            except FloodWaitError as e:
                print(f"⏳ FloodWait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds + 2)
            except Exception as e:
                print(f"❌ Failed to send to {user_id}: {e}")
    else:
        print("⚠️ No users or no config files to send.")

    # Handler برای دستور /start
    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        user_id = event.sender_id
        if user_id not in users:
            users.append(user_id)
            save_users(users)
            print(f"➕ New user via /start: {user_id}")
        await event.respond("✅ ربات فعال است.\nهر ۱۰ دقیقه آخرین کانفیگ‌ها براتون ارسال می‌شود.")

    print("🟢 Bot listening for 40 seconds...")
    await asyncio.sleep(40)
    await client.disconnect()
    print("🏁 BOT FINISHED")

if __name__ == "__main__":
    asyncio.run(main())
