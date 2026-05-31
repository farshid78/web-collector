print("SESSION_STRING:", SESSION_STRING[:20])
import asyncio
import os
import re
import socket
import json
import base64
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError
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


# -----------------------------
# اتصال امن با timeout
# -----------------------------
async def safe_start(client):
    try:
        await asyncio.wait_for(client.start(), timeout=20)
        print("✔ Telegram connected successfully")
        return True
    except asyncio.TimeoutError:
        print("❌ ERROR: Telegram connection timeout (SESSION_STRING probably invalid)")
        return False
    except RPCError as e:
        print("❌ RPC ERROR:", e)
        return False
    except Exception as e:
        print("❌ Unknown error during start():", e)
        return False


# -----------------------------
# استخراج کانفیگ‌ها
# -----------------------------
def extract_configs(text):
    return [
        line.strip()
        for line in text.splitlines()
        if any(line.strip().startswith(s) for s in STARTERS)
    ]


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


# -----------------------------
# استخراج host
# -----------------------------
def extract_host_from_vmess(cfg: str):
    try:
        raw = cfg[len("vmess://"):]
        pad = len(raw) % 4
        if pad:
            raw += "=" * (4 - pad)
        data = base64.b64decode(raw).decode("utf-8", errors="ignore")
        j = json.loads(data)
        return j.get("add") or j.get("host") or j.get("server")
    except:
        return None


def extract_host_from_url(cfg: str):
    try:
        if "://" not in cfg:
            return None
        scheme, rest = cfg.split("://", 1)
        if "@" in rest:
            rest = rest.split("@", 1)[1]
        host = rest.split("/")[0].split(":")[0]
        return host
    except:
        return None


def extract_host(cfg: str):
    if cfg.startswith("vmess://"):
        return extract_host_from_vmess(cfg)
    return extract_host_from_url(cfg)


# -----------------------------
# تشخیص کشور
# -----------------------------
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


# -----------------------------
# اجرای اصلی
# -----------------------------
async def main():
    print("SCRAPER STARTED")

    session = StringSession(SESSION_STRING) if SESSION_STRING else "session"
    client = TelegramClient(session, API_ID, API_HASH)

    # اتصال امن
    ok = await safe_start(client)
    if not ok:
        print("❌ SCRAPER STOPPED — SESSION_STRING INVALID OR TELEGRAM BLOCKED")
        return

    raw = []
    sub_links = []

    # استخراج پیام‌ها
    for ch in CHANNELS:
        print(f"Reading channel: {ch}")
        try:
            entity = await client.get_entity(ch)
        except:
            print(f"❌ Cannot access channel: {ch}")
            continue

        async for msg in client.iter_messages(entity, limit=1000):
            if not msg.message:
                continue

            text = msg.message

            sub_links.extend(SUB_PATTERN.findall(text))
            raw.extend(extract_configs(text))

    # sub لینک‌ها
    sub_configs = []
    for url in sub_links:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                lines = split_stuck_configs(r.text)
                merged = merge_multiline(lines)
                sub_configs.extend(
                    [c for c in merged if any(c.startswith(s) for s in STARTERS)]
                )
        except:
            pass

    # حذف تکراری‌ها
    all_cfgs = list(dict.fromkeys([c.strip() for c in raw + sub_configs if c.strip()]))

    # مسیر ریشه
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # فایل اصلی
    all_file = os.path.join(root, "configs.txt")
    open(all_file, "w").close()

    with open(all_file, "w", encoding="utf-8") as f:
        for c in all_cfgs:
            f.write(c + "\n")

    # -----------------------------
    # ساخت فایل جدا برای هر کشور
    # -----------------------------
    country_files = {}

    for cfg in all_cfgs:
        host = extract_host(cfg)
        cc = get_country_code(host)

        if cc not in country_files:
            country_files[cc] = []

        country_files[cc].append(cfg)

    # ذخیرهٔ فایل‌ها
    for cc, cfgs in country_files.items():
        filename = os.path.join(root, f"configs_{cc}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            for c in cfgs:
                f.write(c + "\n")

    print("RAW:", len(raw))
    print("SUB:", len(sub_configs))
    print("TOTAL:", len(all_cfgs))
    print("COUNTRIES:", list(country_files.keys()))

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
