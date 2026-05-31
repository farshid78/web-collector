import asyncio
import platform
import os
import re
import urllib.request
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network.connection import ConnectionTcpFull
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
MODE = os.getenv("MODE", "USER")

CHANNELS = [
    "V2rayNG_VPN",
    "ShadowProxy66",
    "ConfigsHUB2",
    "free_v2rayyy",
    "v2rayng_config",
    "v2rayng_org",
]

# الگوهای دقیق
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

# ساخت کلاینت
session = StringSession(SESSION_STRING) if SESSION_STRING else "session"
client = TelegramClient(
    session,
    API_ID,
    API_HASH,
    connection=ConnectionTcpFull,
    use_ipv6=False,
)

async def main():
    raw_configs = []
    sub_links = []

    # -------------------------
    # 1) استخراج کانفیگ‌ها از کانال‌ها
    # -------------------------
    for ch in CHANNELS:
        try:
            entity = await client.get_entity(ch)
        except:
            continue

        async for msg in client.iter_messages(entity, limit=1000):
            if not msg.message:
                continue

            for line in msg.message.splitlines():
                line = line.strip()
                if not line:
                    continue

                # کانفیگ‌ها
                for m in PATTERN.findall(line):
                    raw_configs.append(m)

                # sub لینک‌ها
                for s in SUB_PATTERN.findall(line):
                    sub_links.append(s)

    # -------------------------
    # 2) دانلود sub لینک‌ها
    # -------------------------
    sub_configs = []
    for url in sub_links:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if PATTERN.match(line):
                        sub_configs.append(line)
        except:
            pass

    # -------------------------
    # 3) ذخیرهٔ خام
    # -------------------------
    with open("../configs_raw.txt", "w", encoding="utf-8") as f:
        for c in raw_configs:
            f.write(c + "\n")

    with open("../configs_sub.txt", "w", encoding="utf-8") as f:
        for c in sub_configs:
            f.write(c + "\n")

    # -------------------------
    # 4) جدا کردن سالم و خراب
    # -------------------------
    clean = []
    bad = []

    def is_valid(cfg):
        if cfg.startswith("vmess://") and len(cfg) > 20:
            return True
        if cfg.startswith("vless://") and "@" in cfg:
            return True
        if cfg.startswith("trojan://") and "@" in cfg:
            return True
        if cfg.startswith("ss://") and len(cfg) > 10:
            return True
        return False

    for c in raw_configs + sub_configs:
        if is_valid(c):
            clean.append(c)
        else:
            bad.append(c)

    # حذف تکراری‌ها
    clean = list(dict.fromkeys(clean))
    bad = list(dict.fromkeys(bad))

    # -------------------------
    # 5) ذخیرهٔ نهایی
    # -------------------------
    with open("../configs_clean.txt", "w", encoding="utf-8") as f:
        for c in clean:
            f.write(c + "\n")

    with open("../configs_bad.txt", "w", encoding="utf-8") as f:
        for c in bad:
            f.write(c + "\n")

    # فایل نهایی برای ارسال
    with open("../configs_final.txt", "w", encoding="utf-8") as f:
        for c in clean:
            f.write(c + "\n")

    print("RAW:", len(raw_configs))
    print("SUB:", len(sub_configs))
    print("CLEAN:", len(clean))
    print("BAD:", len(bad))

if __name__ == "__main__":
    client.start()
    with client:
        client.loop.run_until_complete(main())
