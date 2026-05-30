import asyncio
import platform

# فقط روی ویندوز لازم داریم
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import re
import socks
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network.connection import ConnectionTcpFull

# -----------------------------
# تنظیمات از محیط (برای GitHub Secrets یا .env)
# -----------------------------
API_ID = int(os.getenv("API_ID", "38225291"))
API_HASH = os.getenv("API_HASH", "ed84535742ca8bb351441b5c77303254")
MODE = os.getenv("MODE", "USER")  # USER یا BOT
SESSION_NAME = "session"
SESSION_STRING = os.getenv("SESSION_STRING", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

CHANNELS = [
    "V2rayNG_VPN",
    "ShadowProxy66",
    "ConfigsHUB2",
    "free_v2rayyy",
    "v2rayng_config",
    "v2rayng_org",
]

PATTERN = re.compile(
    r"(vmess://[A-Za-z0-9+/=]+|"
    r"vless://[^\s]+|"
    r"trojan://[^\s]+|"
    r"ss://[^\s]+)"
)

SUB_PATTERN = re.compile(
    r"https?://[^\s]+\.txt|"
    r"https?://[^\s]+/sub[^\s]*"
)

# -----------------------------
# پروکسی: ویندوز → SOCKS5 محلی / لینوکس → بدون پروکسی
# -----------------------------
if platform.system() == "Windows":
    proxy = (socks.SOCKS5, "127.0.0.1", 10808)
    print("پروکسی SOCKS5 فعال شد:", proxy)
else:
    proxy = None
    print("بدون پروکسی اجرا شد (Linux/GitHub Actions)")

if SESSION_STRING:
    session = StringSession(SESSION_STRING)
else:
    session = SESSION_NAME

client = TelegramClient(
    session,
    API_ID,
    API_HASH,
    connection=ConnectionTcpFull,
    proxy=proxy,
    use_ipv6=False,
    connection_retries=5,
    request_retries=5,
    timeout=10,
    flood_sleep_threshold=30,
)

# -----------------------------
# اسکرپر
# -----------------------------
async def main():
    results = []
    for ch in CHANNELS:
        try:
            entity = await client.get_entity(ch)
        except Exception as e:
            print("خطا در گرفتن کانال:", ch, e)
            continue

        async for msg in client.iter_messages(entity, limit=1000):
            if not msg.message:
                continue
            text = msg.message.replace(" ", "").replace("\n", "")
            for link in PATTERN.findall(text):
                results.append(link)
            for link in SUB_PATTERN.findall(text):
                results.append(link)

    results = list(dict.fromkeys(results))
    with open("../configs.txt", "w", encoding="utf-8") as f:
        for line in results:
            f.write(line + "\n")
    print("تمام شد. تعداد کانفیگ‌ها:", len(results))

# -----------------------------
# اجرای کلاینت
# -----------------------------
if __name__ == "__main__":
    if MODE == "BOT" and BOT_TOKEN:
        client.start(bot_token=BOT_TOKEN)
    else:
        client.start()
    with client:
        client.loop.run_until_complete(main())
