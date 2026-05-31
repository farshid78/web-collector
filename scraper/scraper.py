import os
import re
import socket
import json
import base64
import requests
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

CHANNELS = [
    "filembad", "vpnine1", "ConfigsHUB2", "free_v2rayyy",
    "v2rayng_config", "v2rayng_org", "vasl_bashim", "configs_freeiran",
    "MARTiNCONFiG", "best_internet_iran", "persianvpnhub",
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

def extract_host(cfg: str):
    try:
        if cfg.startswith("vmess://"):
            raw = cfg[len("vmess://"):]
            pad = len(raw) % 4
            if pad:
                raw += "=" * (4 - pad)
            data = base64.b64decode(raw).decode("utf-8", errors="ignore")
            j = json.loads(data)
            return j.get("add") or j.get("host") or j.get("server")
        else:
            _, rest = cfg.split("://", 1)
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            host = rest.split("/")[0].split(":")[0]
            return host
    except:
        return None

def get_country_code(host: str):
    if not host:
        return "UNKNOWN"
    try:
        if not host.replace(".", "").isdigit():
            host = socket.gethostbyname(host)
        r = requests.get(f"http://ip-api.com/json/{host}", timeout=5).json()
        return r.get("countryCode", "UNKNOWN") or "UNKNOWN"
    except:
        return "UNKNOWN"

async def main():
    print("🚀 SCRAPER STARTED (USER MODE)")

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        await asyncio.wait_for(client.connect(), timeout=25)
        if not await client.is_user_authorized():
            print("❌ Session is not authorized!")
            return
        print("✅ User session connected successfully")
    except asyncio.TimeoutError:
        print("❌ Timeout while connecting to Telegram")
        return
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    raw_configs = []
    sub_links = []

    for ch in CHANNELS:
        print(f"📌 Reading channel: {ch}")
        try:
            entity = await client.get_entity(ch)
            print(f"   ✅ Connected to {ch}")

            async for msg in client.iter_messages(entity, limit=350):
                if not msg.message:
                    continue
                text = msg.message
                sub_links.extend(SUB_PATTERN.findall(text))
                raw_configs.extend(extract_configs(text))

        except Exception as e:
            print(f"❌ Error reading {ch}: {e}")
            continue

        await asyncio.sleep(1.5)  # جلوگیری از flood و rate limit

    # پردازش ساب‌لینک‌ها
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
    all_cfgs = list(dict.fromkeys([c.strip() for c in raw_configs + sub_configs if c.strip()]))

    # ذخیره فایل‌ها
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    with open(os.path.join(root, "configs.txt"), "w", encoding="utf-8") as f:
        for c in all_cfgs:
            f.write(c + "\n")

    # دسته‌بندی بر اساس کشور
    country_files = {}
    for cfg in all_cfgs:
        host = extract_host(cfg)
        cc = get_country_code(host)
        country_files.setdefault(cc, []).append(cfg)

    for cc, cfgs in country_files.items():
        filename = os.path.join(root, f"configs_{cc}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            for c in cfgs:
                f.write(c + "\n")

    print(f"✅ Scraping finished → Total: {len(all_cfgs)} configs | Countries: {list(country_files.keys())}")
    await client.disconnect()
    print("🏁 SCRAPER FINISHED SUCCESSFULLY")

if __name__ == "__main__":
    asyncio.run(main())
