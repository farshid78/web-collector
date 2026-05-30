import asyncio
import platform
import os
import re
import urllib.request
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network.connection import ConnectionTcpFull
from dotenv import load_dotenv

# -----------------------------
# تشخیص محیط (Windows یا GitHub)
# -----------------------------
IS_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"

# -----------------------------
# بارگذاری متغیرها
# -----------------------------
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
MODE = os.getenv("MODE", "USER")
SESSION_STRING = os.getenv("SESSION_STRING", "")
SESSION_NAME = "session"
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
# پروکسی فقط روی ویندوز
# -----------------------------
proxy = None

if not IS_GITHUB and platform.system() == "Windows":
    try:
        import socks
        proxy_info = urllib.request.getproxies()

        if "https" in proxy_info:
            url = proxy_info["https"]
        elif "http" in proxy_info:
            url = proxy_info["http"]
        else:
            url = None

        if url:
            if "://" in url:
                url = url.split("://")[1]
            host, port = url.split(":")
            proxy = (socks.SOCKS5, host, int(port))
            print("Windows → پروکسی سیستم شناسایی شد:", proxy)
        else:
            print("Windows → بدون پروکسی")

    except Exception as e:
        print("خطا در تنظیم پروکسی:", e)
        proxy = None

else:
    print("GitHub Actions → بدون پروکسی")

# -----------------------------
# انتخاب نوع سشن
# -----------------------------
if SESSION_STRING:
    session = StringSession(SESSION_STRING)
    print("SESSION_STRING استفاده شد")
else:
    session = SESSION_NAME
    print("SESSION_NAME استفاده شد (سشن فایل لوکال)")

# -----------------------------
# ساخت کلاینت
# -----------------------------
client = TelegramClient(
    session,
    API_ID,
    API_HASH,
    connection=ConnectionTcpFull,
    proxy=proxy,
    use_ipv6=False,
    connection_retries=8,
    request_retries=8,
    timeout=15,
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
