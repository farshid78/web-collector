from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = TelegramClient(None, API_ID, API_HASH)

async def main():
    await client.start(bot_token=BOT_TOKEN)

    # خواندن لیست کاربران
    users = []
    if os.path.exists("users.txt"):
        with open("users.txt") as f:
            users = [line.strip() for line in f.readlines()]

    # ارسال پیام و فایل‌ها
    for user in users:
        try:
            await client.send_message(int(user), "آپدیت جدید آماده شد ✔")
            if os.path.exists("configs.txt"):
                await client.send_file(int(user), "configs.txt")
            if os.path.exists("results.txt"):
                await client.send_file(int(user), "results.txt")
        except Exception as e:
            print("Error sending to", user, e)

    print("Done.")

with client:
    client.loop.run_until_complete(main())
