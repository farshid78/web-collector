import os
import json
import asyncio
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
        print("⚠️ users.json not found. Creating empty file.")
        save_users([])
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
            print(f"📋 Loaded {len(users)} users from users.json")
            return users
    except Exception as e:
        print(f"❌ Error loading users.json: {e}")
        return []

def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except:
        pass

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
        print(f"❌ ERROR connecting bot: {e}")
        return

    users = load_users()
    config_files = get_config_files()

    if not config_files:
        print("❌ No config files found! Cannot send anything.")
    elif not users:
        print("⚠️ No users registered yet. Waiting for /start commands.")
    else:
        print(f"📤 Starting to send {len(config_files)} files to {len(users)} users...")

        for i, user_id in enumerate(users, 1):
            print(f"[{i}/{len(users)}] Sending to user {user_id} ...")
            try:
                await client.send_message(user_id, "🟢 آپدیت جدید کانفیگ‌ها آماده شد!")
                
                for file in config_files:
                    print(f"   ↳ Sending file: {file}")
                    await client.send_file(user_id, file)
                    await asyncio.sleep(1.2)  # جلوگیری از flood

                print(f"✅ Successfully sent to user {user_id}")
                
            except FloodWaitError as e:
                print(f"⏳ FloodWait: Sleeping {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Failed to send to {user_id}: {e}")

    # ثبت handler برای /start
    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        user_id = event.sender_id
        if user_id not in users:
            users.append(user_id)
            save_users(users)
            print(f"➕ New user added: {user_id}")
        else:
            print(f"👤 User {user_id} already exists")
        
        await event.respond(
            "سلام! 👋\n\n"
            "✅ من فعالم و هر ۱۰ دقیقه کانفیگ‌های جدید رو براتون می‌فرستم.\n"
            "برای دریافت دستی هم می‌تونی صبر کنی تا آپدیت بعدی."
        )

    print("🟢 Bot is now running and listening...")
    # برای GitHub Actions فقط ۳۰ ثانیه منتظر می‌ماند و بعد خاموش می‌شود
    await asyncio.sleep(30)
    
    await client.disconnect()
    print("🏁 BOT FINISHED")

if __name__ == "__main__":
    asyncio.run(main())
