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
    "filembad",
    "vpnine1",
    "ConfigsHUB2",
    "free_v2rayyy",
    "v2rayng_config",
    "v2rayng_org",
    "vasl_bashim",
    "configs_freeiran",
    "MARTiNCONFiG",
    "best_internet_iran",
    "persianvpnhub",
    
]

STARTERS = ["vmess://", "vless://", "trojan://", "ss://"]
SUB_PATTERN = re.compile(r"https?://[^\s]+(?:\.txt|/sub[^\s]*)")


def extract_configs(text):
    return [line.strip() for line in text.splitlines() if any(line.strip().startswith(s) for s in STARTERS)]


def split_stuck_configs(text):
    for s in STARTERS[1:]:
        text = text.replace(s, "\n" + s)
    return text.splitlines()


def merge_multiline(lines):
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

    # استخراج پیام‌ها
    for ch in CHANNELS:
        try:
            entity = await client.get_entity(ch)
        except:
            continue

        async for msg in client.iter_messages(entity, limit=1000):
            if not msg.message:
                continue

            text = msg.message

            sub_links.extend(SUB_PATTERN.findall(text))
            raw.extend(extract_configs(text))

    # دانلود sub لینک‌ها
    sub_configs = []
    for url in sub_links:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                lines = split_stuck_configs(r.text)
                merged = merge_multiline(lines)
                sub_configs.extend([c for c in merged if any(c.startswith(s) for s in STARTERS)])
        except:
            pass

    # حذف تکراری‌ها
    all_cfgs = list(dict.fromkeys([c.strip() for c in raw + sub_configs if c.strip()]))

    # ذخیره نهایی configs.txt در ریشه
    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs.txt"))

    open(out_file, "w").close()

    with open(out_file, "w", encoding="utf-8") as f:
        for c in all_cfgs:
            f.write(c + "\n")

    print("RAW:", len(raw))
    print("SUB:", len(sub_configs))
    print("TOTAL:", len(all_cfgs))

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
