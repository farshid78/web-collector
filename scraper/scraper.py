import asyncio
import os
import re
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

CHANNELS = [
    "V2rayNG_VPN",
    "ShadowProxy66",
    "ConfigsHUB2",
    "free_v2rayyy",
    "v2rayng_config",
    "v2rayng_org",
]

# شروع کانفیگ‌ها
STARTERS = ["vmess://", "vless://", "trojan://", "ss://"]

# sub لینک‌ها
SUB_PATTERN = re.compile(r"https?://[^\s]+(?:\.txt|/sub[^\s]*)")


def extract_configs(text):
    """فقط خطوطی که کانفیگ واقعی هستند را استخراج می‌کند"""
    configs = []
    for line in text.splitlines():
        line = line.strip()
        if any(line.startswith(s) for s in STARTERS):
            configs.append(line)
    return configs


def split_stuck_configs(text):
    """جدا کردن کانفیگ‌های چسبیده"""
    for s in STARTERS[1:]:
        text = text.replace(s, "\n" + s)
    return text.splitlines()


def merge_multiline(lines):
    """ترکیب کانفیگ‌های چندخطی"""
    merged = []
    current = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if any(line.startswith(s) for s in STARTERS):
            if current:
                merged.append(current)
            current = line
        else:
            current += line

    if current:
        merged.append(current)

    return merged


async def main():
    session = StringSession(SESSION_STRING) if SESSION_STRING else "session"
    client = TelegramClient(session, API_ID, API_HASH)
    await client.start()

    raw = []
    sub_links = []

    # -------------------------
    # 1) استخراج پیام‌ها
    # -------------------------
    for ch in CHANNELS:
        try:
            entity = await client.get_entity(ch)
        except:
            continue

        async for msg in client.iter_messages(entity, limit=1000):
            if not msg.message:
                continue

            text = msg.message

            # sub لینک‌ها
            for s in SUB_PATTERN.findall(text):
                sub_links.append(s)

            # فقط کانفیگ‌های واقعی را استخراج کن
            configs = extract_configs(text)
            raw.extend(configs)

    # -------------------------
    # 2) دانلود sub لینک‌ها
    # -------------------------
    sub_configs = []
    for url in sub_links:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                lines = split_stuck_configs(r.text)
                merged = merge_multiline(lines)
                # فقط کانفیگ‌های واقعی
                configs = [c for c in merged if any(c.startswith(s) for s in STARTERS)]
                sub_configs.extend(configs)
        except:
            pass

    # -------------------------
    # 3) حذف تکراری‌ها
    # -------------------------
    all_cfgs = raw + sub_configs
    all_cfgs = [c.strip() for c in all_cfgs if c.strip()]
    all_cfgs = list(dict.fromkeys(all_cfgs))

    # -------------------------
    # 4) ذخیره نهایی
    # -------------------------
    with open("configs_final.txt", "w", encoding="utf-8") as f:
        for c in all_cfgs:
            f.write(c + "\n")

    print("RAW:", len(raw))
    print("SUB:", len(sub_configs))
    print("TOTAL:", len(all_cfgs))


if __name__ == "__main__":
    asyncio.run(main())
