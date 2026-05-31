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
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def get_config_files():
    files = [f for f in os.listdir(".") if f.startswith("configs") and f.endswith(".txt")]
    return sorted(files)

async def main():
    print("🤖 BOT STARTED")

    client = TelegramClient("bot_session", API_ID, API_HASH)

    try:
        await client.start(bot_token=BOT_TOKEN)
        print("✅ Bot connected successfully")
    except Exception as e:
        print(f"❌ ERROR connecting bot: {e}")
        return

    users = load_users()

    @client.on(events.NewMessage(pattern="/start"))
    async def start_handler(event):
        user_id = event.sender_id
        if user_id not in users:
            users.append(user_id)
            save_users(users)
            print(f"✔ New user added: {user_id}")
        await event.respond(
            "سلام! 👋\n"
            "من هر ۱۰ دقیقه آخرین کانفیگ‌های V2Ray رو براتون می‌فرستم.\n"
            "فقط صبر کن تا آپدیت بعدی برسه."
        )

    # ارسال اولیه بعد از استارت
    config_files = get_config_files()
    if config_files:
        print(f"📤 Sending {len(config_files)} config files to {len(users)} users")
        for user_id in users:
            try:
                await client.send_message(user_id, "آپدیت جدید کانفیگ‌ها آماده شد ✅")
                for file in config_files:
                    await client.send_file(user_id, file)
                    await asyncio.sleep(1)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"Error sending to {user_id}: {e}")

    await client.disconnect()
    print("🏁 BOT FINISHED")

if __name__ == "__main__":
    asyncio.run(main())
