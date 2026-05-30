import asyncio
import platform

# روی ویندوز برای سازگاری با asyncio
if platform.system() == "Windows":
    proxy = None
    print("Windows → اتصال مستقیم بدون پروکسی")
else:
    proxy = None
    print("Linux/GitHub Actions → بدون پروکسی")

import os
import re
import urllib.request
import socks
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network.connection import ConnectionTcpFull
from dotenv import load_dotenv

# -----------------------------
# بارگذاری متغیرها از .env (فقط روی ویندوز)
# -----------------------------
load_dotenv()

# -----------------------------
# تنظیمات از محیط (روی ویندوز از .env، روی GitHub از Secrets)
# -----------------------------
API_ID = int(os.getenv("API_ID", "0"))  # این مقدار باید در .env یا GitHub Secrets تنظیم شود
API_HASH = os.getenv("API_HASH", "")    # اینجا API_HASH تلگرام (در .env یا Secrets)
MODE = os.getenv("MODE", "USER")        # USER یا BOT
SESSION_STRING = os.getenv("SESSION_STRING", "")  # اینجا SESSION_STRING که ساختی
SESSION_NAME = "session"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # اگر از ربات استفاده می‌کنی، توکن ربات را اینجا (در .env یا Secrets)

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
# تشخیص پروکسی سیستم روی ویندوز
# -----------------------------
def get_system_proxy():
    """
    پروکسی سیستم ویندوز را می‌خواند.
    اگر VPN/Proxy روی سیستم تنظیم شده باشد، اینجا شناسایی می‌شود.
    """
    try:
        proxy = urllib.request.getproxies()

        if "https" in proxy:
            url = proxy["https"]
        elif "http" in proxy:
            url = proxy["http"]
        else:
            return None

        if "://" in url:
            url = url.split("://")[1]

        host, port = url.split(":")
        return host, int(port)

    except:
        return None

# -----------------------------
# انتخاب پروکسی
# -----------------------------
if platform.system() == "Windows":
    system_proxy = get_system_proxy()

    if system_proxy:
        host, port = system_proxy
        proxy = (socks.SOCKS5, host, port)
        print("پروکسی سیستم شناسایی شد:", proxy)
    else:
        proxy = None
        print("هیچ پروکسی سیستمی پیدا نشد (اتصال مستقیم)")
else:
    proxy = None
    print("Linux/GitHub Actions → بدون پروکسی")

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
