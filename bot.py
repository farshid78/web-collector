import os
import json
import asyncio
import requests
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from dotenv import load_dotenv

load_dotenv()  # بارگذاری متغیرهای محیطی از فایل .env

API_ID = int(os.getenv("API_ID", "0"))                    # دریافت API ID از محیط
API_HASH = os.getenv("API_HASH", "")                      # دریافت API Hash از محیط
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")           # توکن ربات تلگرام
USERS_FILE = "users.json"                                 # فایل ذخیره‌سازی اطلاعات کاربران

# لیست دقیق فایل‌هایی که می‌خواهیم ارسال شود
DESIRED_FILES = [
    "configs.txt",
    "configs_IR.txt",
    "configs_TR.txt",
    "configs_US.txt",
    "configs_DE.txt",
    "configs_NL.txt",
    "configs_FI.txt",
    "configs_SG.txt",
    "configs_AE.txt",
    "configs_others.txt"
]

# -----------------------------
# مدیریت کاربران
# -----------------------------
def load_users():
    """بارگذاری لیست کاربران از فایل JSON"""
    if not os.path.exists(USERS_FILE):
        save_users([])          # اگر فایل وجود نداشت، فایل جدید بساز
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    """ذخیره لیست کاربران در فایل JSON"""
    users = list(dict.fromkeys(users))   # حذف تکراری‌ها
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def get_users_from_telegram():
    """دریافت کاربران جدید از طریق getUpdates تلگرام"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?allowed_updates=message"
        r = requests.get(url, timeout=8)
        if r.status_code != 200:
            return []
        return [
            update["message"]["from"]["id"]
            for update in r.json().get("result", [])
            if "message" in update and "from" in update["message"]
        ]
    except:
        return []

# -----------------------------
# دریافت فایل‌های کانفیگ (اصلاح شده)
# -----------------------------
def get_config_files():
    """برگرداندن فقط فایل‌های مورد نظر که وجود دارند و خالی نیستند"""
    files = []
    for file in DESIRED_FILES:
        if os.path.exists(file) and os.path.getsize(file) > 0:
            files.append(file)
   
    print("📁 Files to send:", files)
    return files

# -----------------------------
# اجرای اصلی بات
# -----------------------------
async def main():
    """تابع اصلی اجرای ربات"""
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
            # پیام اطلاع‌رسانی
            await client.send_message(
                user_id,
                "🟢 **آپدیت جدید کانفیگ‌ها آماده شد**\n"
                "فایل‌ها بر اساس کشور دسته‌بندی شده‌اند:"
            )
            
            # ارسال فایل‌ها
            for file in config_files:
                print(f" ↳ Sending {file}")
                await client.send_file(user_id, file)
                await asyncio.sleep(1.3)   # جلوگیری از FloodWait

            print(f"✅ Done for {user_id}")

        except FloodWaitError as e:
            print(f"⏳ FloodWait: {e.seconds} sec")
            await asyncio.sleep(e.seconds + 3)
        except Exception as e:
            print(f"❌ Error sending to {user_id}: {e}")

    # هندلر دستور /start
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

    await asyncio.sleep(25)          # زمان برای پردازش رویدادها
    await client.disconnect()
    print("🏁 BOT FINISHED")

if __name__ == "__main__":
    asyncio.run(main())
