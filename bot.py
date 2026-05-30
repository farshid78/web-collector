from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = TelegramClient("bot_session", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# -----------------------------
# /start → ثبت کاربر
# -----------------------------
@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    chat_id = event.chat_id

    # ذخیره chat_id در فایل
    with open("users.txt", "a") as f:
        f.write(str(chat_id) + "\n")

    await event.respond(
        "سلام! 👋\n"
        "شما با موفقیت ثبت شدید.\n"
        "هر ۱۵ دقیقه آخرین کانفیگ‌ها برای شما ارسال می‌شود."
    )

print("ربات فعال شد...")
client.run_until_disconnected()
