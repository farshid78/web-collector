from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
import os
import subprocess

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = TelegramClient("bot_session_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    chat_id = event.chat_id

    # ذخیره chat_id
    with open("users.txt", "a") as f:
        f.write(str(chat_id) + "\n")

    # پیام خوش‌آمد
    await event.respond(
        "سلام! 👋\n"
        "شما با موفقیت ثبت شدید.\n"
        "هر ۱۵ دقیقه آخرین کانفیگ‌ها برای شما ارسال می‌شود."
    )

    # commit و push اتوماتیک
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"])
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"])
    subprocess.run(["git", "add", "users.txt"])
    subprocess.run(["git", "commit", "-m", "Add new user"])
    subprocess.run(["git", "push"])

print("ربات فعال شد...")
client.run_until_disconnected()
