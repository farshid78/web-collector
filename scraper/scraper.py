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
from telethon.errors import FloodWaitError
from dotenv import load_dotenv

load_dotenv()

print("🔧 DEBUG: Script started", file=sys.stderr)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

print(f"🔧 DEBUG: SESSION_STRING length: {len(SESSION_STRING)}", file=sys.stderr)

CHANNELS = [
    "filembad", "vpnine1", "ConfigsHUB2", "free_v2rayyy",
    "v2rayng_config", "v2rayng_org", "vasl_bashim", "configs_freeiran",
    "MARTiNCONFiG", "best_internet_iran", "persianvpnhub",
]

STARTERS = ["vmess://", "vless://", "trojan://", "ss://"]
SUB_PATTERN = re.compile(r"https?://[^\s]+(?:\.txt|/sub[^\s]*)")

# ==================== Cache برای Country ====================
country_cache = {}

def extract_configs(text):
    return [line.strip() for line in text.splitlines() if any(line.strip().startswith(s) for s in STARTERS)]

def split_stuck_configs(text):
    for s in STARTERS[1:]:
        text = text.replace(s, "\n" + s)
    return [line.strip() for line in text.splitlines() if line.strip()]

def merge_multiline(lines):
    merged = []
    current = ""
    for line in lines:
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
            raw = cfg[8:]
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
            return rest.split("/")[0].split(":")[0].split("?")[0]
    except:
        return None

def get_country_code(host: str):
    if not host:
        return "UNKNOWN"
    
    if host in country_cache:
        return country_cache[host]

    try:
        # DNS Resolve
        if not host.replace(".", "").isdigit():
            host = socket.gethostbyname(host)

        # درخواست بهینه
        r = requests.get(
            f"http://ip-api.com/json/{host}?fields=countryCode",
            timeout=2.5
        )
        cc = r.json().get("countryCode", "UNKNOWN") or "UNKNOWN"
    except:
        cc = "UNKNOWN"

    country_cache[host] = cc
    return cc

# ==================== Main ====================
async def main():
    print("🚀 SCRAPER STARTED (USER MODE)", flush=True)

    if not SESSION_STRING:
        print("❌ SESSION_STRING is empty!", flush=True)
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        print("⏳ Connecting...", flush=True)
        await asyncio.wait_for(client.connect(), timeout=30)
        if not await client.is_user_authorized():
            print("❌ SESSION NOT AUTHORIZED", flush=True)
            return
        print("✅ Login successful!", flush=True)
    except Exception as e:
        print(f"❌ Connection Error: {e}", flush=True)
        return

    raw_configs = []
    sub_links = []

    # ==================== Reading Channels ====================
    for ch in CHANNELS:
        print(f"📌 Reading channel: {ch}", flush=True)
        try:
            entity = await client.get_entity(ch)
            count = 0

            async for msg in client.iter_messages(entity, limit=150):  # بهینه شده
                if msg.message:
                    text = msg.message
                    sub_links.extend(SUB_PATTERN.findall(text))
                    raw_configs.extend(extract_configs(text))
                    count += 1

                if count % 40 == 0:
                    await asyncio.sleep(0.6)

            print(f"   📥 Fetched {count} messages from {ch}", flush=True)

        except FloodWaitError as e:
            print(f"   ⏳ FloodWait in {ch}: {e.seconds}s", flush=True)
            await asyncio.sleep(e.seconds + 3)
        except Exception as e:
            print(f"   ❌ Error in {ch}: {e}", flush=True)

        await asyncio.sleep(1.5)  # بین چنل‌ها

    # ==================== Debug Info ====================
    print(f"📦 Raw configs collected: {len(raw_configs)}", flush=True)
    print(f"🔗 Sub links found: {len(sub_links)}", flush=True)

    # ==================== Process Sub Links (بهینه) ====================
    sub_configs = []
    for url in sub_links[:20]:        # محدود شده
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200:
                merged = merge_multiline(split_stuck_configs(r.text))
                sub_configs.extend([c for c in merged if any(c.startswith(s) for s in STARTERS)])
        except:
            continue

    print(f"📥 Sub configs extracted: {len(sub_configs)}", flush=True)

    # ==================== Final Merge ====================
    all_cfgs = list(dict.fromkeys([c.strip() for c in raw_configs + sub_configs if c.strip()]))

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    with open(os.path.join(root, "configs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(all_cfgs))

    # ==================== Country Split با Progress ====================
    print("🌍 Starting country detection...", flush=True)
    country_map = {}

    for i, cfg in enumerate(all_cfgs, 1):
        host = extract_host(cfg)
        cc = get_country_code(host)
        
        country_map.setdefault(cc, []).append(cfg)

        if i % 100 == 0 or i == len(all_cfgs):
            print(f"   🌍 Processed {i}/{len(all_cfgs)} configs...", flush=True)

    # Save files
    for cc, cfgs in country_map.items():
        filename = os.path.join(root, f"configs_{cc}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(cfgs))

    print("🌍 Countries found:", sorted(country_map.keys()), flush=True)
    print(f"📦 Total unique configs: {len(all_cfgs)}", flush=True)
    print("🏁 SCRAPER COMPLETED SUCCESSFULLY", flush=True)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
