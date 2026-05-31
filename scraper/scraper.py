import os
import re
import socket
import json
import base64
import requests
import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

print("🔧 DEBUG: Script started", file=sys.stderr)
print("🔧 DEBUG: Python version:", sys.version, file=sys.stderr)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

print(f"🔧 DEBUG: API_ID loaded: {bool(API_ID)}", file=sys.stderr)
print(f"🔧 DEBUG: API_HASH loaded: {bool(API_HASH)}", file=sys.stderr)
print(f"🔧 DEBUG: SESSION_STRING length: {len(SESSION_STRING)}", file=sys.stderr)

CHANNELS = [
    "filembad", "vpnine1", "ConfigsHUB2", "free_v2rayyy",
    "v2rayng_config", "v2rayng_org", "vasl_bashim", "configs_freeiran",
    "MARTiNCONFiG", "best_internet_iran", "persianvpnhub",
]

STARTERS = ["vmess://", "vless://", "trojan://", "ss://"]
SUB_PATTERN = re.compile(r"https?://[^\s]+(?:\.txt|/sub[^\s]*)")

# ==================== توابع استخراج (بدون تغییر) ====================
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
        if not line: continue
        if any(line.startswith(s) for s in STARTERS):
            if current: merged.append(current)
            current = line
        else:
            current += line
    if current: merged.append(current)
    return merged

def extract_host(cfg: str):
    try:
        if cfg.startswith("vmess://"):
            raw = cfg[8:]
            pad = len(raw) % 4
            if pad: raw += "=" * (4 - pad)
            data = base64.b64decode(raw).decode("utf-8", errors="ignore")
            j = json.loads(data)
            return j.get("add") or j.get("host") or j.get("server")
        else:
            _, rest = cfg.split("://", 1)
            if "@" in rest: rest = rest.split("@", 1)[1]
            host = rest.split("/")[0].split(":")[0]
            return host
    except:
        return None

def get_country_code(host: str):
    if not host: return "UNKNOWN"
    try:
        if not host.replace(".", "").isdigit():
            host = socket.gethostbyname(host)
        r = requests.get(f"http://ip-api.com/json/{host}", timeout=6).json()
        return r.get("countryCode", "UNKNOWN")
    except:
        return "UNKNOWN"

# ==================== Main ====================
async def main():
    print("🚀 SCRAPER STARTED (USER MODE)", flush=True)

    if not SESSION_STRING:
        print("❌ SESSION_STRING is empty!", flush=True)
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        print("⏳ Connecting to Telegram...", flush=True)
        await asyncio.wait_for(client.connect(), timeout=30)
        print("🔌 Connected. Checking authorization...", flush=True)
        
        if not await client.is_user_authorized():
            print("❌ Session is NOT authorized!", flush=True)
            return

        print("✅ Login successful!", flush=True)

    except asyncio.TimeoutError:
        print("❌ Timeout while connecting to Telegram", flush=True)
        return
    except Exception as e:
        print(f"❌ Connection Error: {type(e).__name__}: {e}", flush=True)
        return

    # بقیه کد (خواندن کانال‌ها)
    raw_configs = []
    sub_links = []

    for ch in CHANNELS:
        print(f"📌 Reading channel: {ch}", flush=True)
        try:
            entity = await client.get_entity(ch)
            print(f"   ✅ Connected to {ch}", flush=True)

            count = 0
            async for msg in client.iter_messages(entity, limit=250):
                if msg.message:
                    text = msg.message
                    sub_links.extend(SUB_PATTERN.findall(text))
                    raw_configs.extend(extract_configs(text))
                count += 1
                if count % 50 == 0:
                    print(f"   Processed {count} messages from {ch}", flush=True)

        except Exception as e:
            print(f"❌ Error in {ch}: {e}", flush=True)
            continue

        await asyncio.sleep(2)

    # پردازش نهایی
    sub_configs = []
    for url in sub_links[:30]:   # محدود کردن برای سرعت
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                sub_configs.extend(merge_multiline(split_stuck_configs(r.text)))
        except:
            pass

    all_cfgs = list(dict.fromkeys([c.strip() for c in raw_configs + sub_configs if c.strip()]))

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    with open(os.path.join(root, "configs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(all_cfgs))

    print(f"✅ Finished! Total configs: {len(all_cfgs)}", flush=True)
    await client.disconnect()
    print("🏁 SCRAPER COMPLETED", flush=True)

if __name__ == "__main__":
    print("🔧 Starting asyncio.run...", flush=True)
    asyncio.run(main())
