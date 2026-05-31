from dotenv import load_dotenv
load_dotenv()

from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os
import asyncio
import sys

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MODE = os.getenv("MODE", "LISTEN")  # LISTEN یا SEND

client = TelegramClient(StringSession(""), API_ID, API_HASH)

USERS_FILE = "users.txt"


def add_user(user_id: int):
    user_id = str(user_id)

    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(user_id + "\n")
        return

    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()

    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(user_id + "\n")


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    user_id = event.sender_id
    add_user(user_id)
    await event.respond("سلام! شما با موفقیت ثبت شدید ✔")


async def send_updates():
    await client.start(bot_token=BOT_TOKEN)

    if os.path.exists("users.txt"):
        with open("users.txt") as f:
            users = [line.strip() for line in f.readlines()]
    else:
        users = []

    for user in users:
        try:
            uid = int(user)
            await client.send_message(uid, "آپدیت جدید آماده شد ✔")

            if os.path.exists("configs.txt"):
                await client.send_file(uid, "configs.txt")

            if os.path.exists("results.txt"):
                await client.send_file(uid, "results.txt")

        except Exception as e:
            print("Error sending to", user, e)

    print("Done.")
    await client.disconnect()
    sys.exit(0)


if __name__ == "__main__":
    if MODE == "SEND":
        asyncio.run(send_updates())
    else:
        client.start(bot_token=BOT_TOKEN)
        client.run_until_disconnected()
