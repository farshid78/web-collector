import os
import re
import json
import time
import base64
import socket
import asyncio
import logging
import tempfile
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ==========================================================
# ENV
# ==========================================================
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# ==========================================================
# VALIDATION
# ==========================================================
if not API_ID:
    raise RuntimeError("❌ API_ID missing")

if not API_HASH:
    raise RuntimeError("❌ API_HASH missing")

if not SESSION_STRING:
    raise RuntimeError("❌ SESSION_STRING missing")

# ==========================================================
# LOGGING
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("SCRAPER")

logger.info("🔧 SCRAPER INITIALIZING")
logger.info(f"🔧 SESSION_STRING length: {len(SESSION_STRING)}")

# ==========================================================
# CONFIG
# ==========================================================
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

STARTERS = [
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
]

IMPORTANT_COUNTRIES = {
    "IR",
    "TR",
    "US",
    "DE",
    "NL",
    "FI",
    "SG",
    "AE",
}

SUB_PATTERN = re.compile(
    r"https?://[^\s]+(?:\.txt|/sub[^\s]*)",
    re.IGNORECASE,
)

ROOT_DIR = Path(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

COUNTRY_CACHE_FILE = ROOT_DIR / "country_cache.json"

MAX_SUB_LINKS = 10
THREAD_POOL_WORKERS = 16
HTTP_TIMEOUT = 4
CHANNEL_MESSAGE_LIMIT = 100

# ==========================================================
# REQUEST SESSION (FASTER)
# ==========================================================
session = requests.Session()

adapter = requests.adapters.HTTPAdapter(
    pool_connections=25,
    pool_maxsize=25,
)

session.mount("http://", adapter)
session.mount("https://", adapter)

session.headers.update({
    "User-Agent": "Mozilla/5.0 scraper"
})

# ==========================================================
# COUNTRY CACHE
# ==========================================================
country_cache = {}


def load_country_cache():
    global country_cache

    try:
        if COUNTRY_CACHE_FILE.exists():
            with open(
                COUNTRY_CACHE_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                country_cache = json.load(f)

            logger.info(
                f"🌍 Loaded country cache: "
                f"{len(country_cache)}"
            )
    except Exception as e:
        logger.warning(
            f"⚠️ Failed loading cache: {e}"
        )
        country_cache = {}


def save_country_cache():
    try:
        temp_path = (
            str(COUNTRY_CACHE_FILE)
            + ".tmp"
        )

        with open(
            temp_path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                country_cache,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_path,
            COUNTRY_CACHE_FILE
        )

    except Exception as e:
        logger.warning(
            f"⚠️ Failed saving cache: {e}"
        )

# ==========================================================
# SAFE NETWORK REQUEST
# ==========================================================
def safe_request(
    url,
    timeout=HTTP_TIMEOUT,
    retries=3
):
    """
    Safe request with retry
    """

    for attempt in range(retries):

        try:
            response = session.get(
                url,
                timeout=timeout
            )

            if response.status_code == 200:
                return response

        except Exception:
            pass

        sleep_time = (
            0.7 * (attempt + 1)
        )

        time.sleep(sleep_time)

    return None

# ==========================================================
# FILE SAVE (ATOMIC)
# ==========================================================
def atomic_write(
    path: str,
    content: str
):
    """
    Prevent broken files
    """

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8"
        ) as tf:

            tf.write(content)
            temp_name = tf.name

        os.replace(
            temp_name,
            path
        )

    except Exception as e:
        logger.error(
            f"❌ Atomic write failed "
            f"{path}: {e}"
        )

# ==========================================================
# HELPERS
# ==========================================================
def is_config(text: str):
    return any(
        text.startswith(s)
        for s in STARTERS
    )


def normalize_config(cfg: str):
    """
    Keep behavior same
    only sanitize lightly
    """

    if not cfg:
        return ""

    cfg = cfg.strip()
    cfg = cfg.replace("\r", "")

    return cfg


def dedupe_preserve_order(items):
    seen = set()
    output = []

    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)

    return output
    # ==========================================================
# CONFIG EXTRACTION
# ==========================================================
def extract_configs(text: str):
    """
    Extract configs from message
    Keep behavior identical
    """

    if not text:
        return []

    configs = []

    try:
        for line in text.splitlines():

            line = normalize_config(line)

            if is_config(line):
                configs.append(line)

    except Exception as e:
        logger.warning(
            f"⚠️ extract_configs error: {e}"
        )

    return configs


def split_stuck_configs(text: str):
    """
    Fix merged configs
    Example:
    vmess://....vless://...
    """

    if not text:
        return []

    try:
        for starter in STARTERS[1:]:
            text = text.replace(
                starter,
                "\n" + starter
            )

        return [
            normalize_config(x)
            for x in text.splitlines()
            if normalize_config(x)
        ]

    except Exception as e:
        logger.warning(
            f"⚠️ split_stuck_configs error: {e}"
        )
        return []


def merge_multiline(lines):
    """
    Merge broken multiline configs
    Preserve old behavior
    """

    merged = []
    current = ""

    try:
        for line in lines:

            line = normalize_config(line)

            if not line:
                continue

            if is_config(line):

                if current:
                    merged.append(current)

                current = line

            else:
                current += line

        if current:
            merged.append(current)

    except Exception as e:
        logger.warning(
            f"⚠️ merge_multiline error: {e}"
        )

    return merged


# ==========================================================
# HOST EXTRACTION
# ==========================================================
def extract_host(cfg: str):
    """
    Extract host/IP from config
    """

    try:
        if cfg.startswith("vmess://"):

            raw = cfg[8:]

            padding = len(raw) % 4
            if padding:
                raw += "=" * (
                    4 - padding
                )

            decoded = (
                base64
                .b64decode(raw)
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )

            data = json.loads(decoded)

            return (
                data.get("add")
                or data.get("host")
                or data.get("server")
            )

        else:
            _, rest = cfg.split(
                "://",
                1
            )

            if "@" in rest:
                rest = rest.split(
                    "@",
                    1
                )[1]

            host = (
                rest
                .split("/")[0]
                .split(":")[0]
                .split("?")[0]
            )

            return host

    except Exception:
        return None


# ==========================================================
# SUBSCRIPTION FETCH
# ==========================================================
def fetch_subscription(url):
    """
    Fetch subscription configs
    Safe + retry
    """

    try:
        response = safe_request(
            url,
            timeout=4,
            retries=2
        )

        if not response:
            return []

        text = response.text

        if not text.strip():
            return []

        merged = merge_multiline(
            split_stuck_configs(text)
        )

        return [
            normalize_config(c)
            for c in merged
            if is_config(c)
        ]

    except Exception as e:
        logger.warning(
            f"⚠️ subscription error "
            f"{url}: {e}"
        )

        return []


def fetch_subscriptions_parallel(
    urls
):
    """
    Parallel fetch
    Faster GitHub runtime
    """

    urls = urls[:MAX_SUB_LINKS]

    if not urls:
        return []

    logger.info(
        f"🌐 Fetching "
        f"{len(urls)} subscriptions"
    )

    collected = []

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:

        futures = {
            executor.submit(
                fetch_subscription,
                url
            ): url
            for url in urls
        }

        for future in as_completed(
            futures
        ):

            url = futures[future]

            try:
                result = future.result()

                if result:
                    collected.extend(
                        result
                    )

                    logger.info(
                        f"📥 SUB OK "
                        f"{url} "
                        f"({len(result)})"
                    )

            except Exception as e:
                logger.warning(
                    f"⚠️ SUB FAIL "
                    f"{url}: {e}"
                )

    return collected


# ==========================================================
# DEDUPE + SANITIZE
# ==========================================================
def sanitize_configs(configs):
    """
    Keep behavior same
    Light sanitize only
    """

    cleaned = []

    for cfg in configs:

        cfg = normalize_config(cfg)

        if not cfg:
            continue

        if not is_config(cfg):
            continue

        cleaned.append(cfg)

    return cleaned


def dedupe_configs(configs):
    """
    Strong dedupe
    preserve order
    """

    seen = set()
    unique = []

    for cfg in configs:

        key = cfg.strip()

        if key not in seen:
            seen.add(key)
            unique.append(cfg)

    return unique
    # ==========================================================
# COUNTRY DETECTION
# ==========================================================
def resolve_host(host: str):
    """
    Resolve domain → IP safely
    """

    try:
        if not host:
            return None

        host = host.strip()

        if not host:
            return None

        # already IP
        if host.replace(".", "").isdigit():
            return host

        return socket.gethostbyname(host)

    except Exception:
        return None


def get_country_code(host: str):
    """
    Get country code
    with cache + retry
    """

    if not host:
        return "UNKNOWN"

    host = host.strip()

    if not host:
        return "UNKNOWN"

    # ==========================
    # CACHE
    # ==========================
    cached = country_cache.get(host)

    if cached:
        return cached

    try:
        ip = resolve_host(host)

        if not ip:
            country_cache[host] = "UNKNOWN"
            return "UNKNOWN"

        url = (
            f"http://ip-api.com/json/"
            f"{ip}"
            f"?fields=countryCode"
        )

        response = safe_request(
            url,
            timeout=3,
            retries=2
        )

        if response:

            try:
                cc = (
                    response.json()
                    .get(
                        "countryCode",
                        "UNKNOWN"
                    )
                )

                if not cc:
                    cc = "UNKNOWN"

            except Exception:
                cc = "UNKNOWN"

        else:
            cc = "UNKNOWN"

    except Exception:
        cc = "UNKNOWN"

    # ==========================
    # SAVE CACHE
    # ==========================
    country_cache[host] = cc

    return cc


# ==========================================================
# COUNTRY BATCH PROCESSING
# ==========================================================
def batch_get_countries(
    configs
):
    """
    Multi-thread country detection
    Fast + safe
    """

    total = len(configs)

    logger.info(
        f"🌍 Starting country "
        f"detection ({total})"
    )

    country_map = {}

    if not configs:
        return country_map

    max_workers = min(
        THREAD_POOL_WORKERS,
        20
    )

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {}

        for cfg in configs:

            try:
                host = extract_host(cfg)

                future = executor.submit(
                    get_country_code,
                    host
                )

                futures[future] = cfg

            except Exception:
                continue

        completed = 0

        for future in as_completed(
            futures
        ):

            cfg = futures[future]

            try:
                cc = future.result()

                if not cc:
                    cc = "UNKNOWN"

            except Exception:
                cc = "UNKNOWN"

            country_map.setdefault(
                cc,
                []
            ).append(cfg)

            completed += 1

            if (
                completed % 150 == 0
                or completed == total
            ):
                logger.info(
                    f"🌍 Country detection "
                    f"{completed}/{total}"
                )

    return country_map


# ==========================================================
# SAVE CONFIG FILES
# ==========================================================
def save_country_files(
    root_path,
    country_map
):
    """
    Save country grouped files
    Keep same behavior
    """

    others = []

    for cc, cfgs in country_map.items():

        try:
            if cc in IMPORTANT_COUNTRIES:

                file_path = os.path.join(
                    root_path,
                    f"configs_{cc}.txt"
                )

                atomic_write(
                    file_path,
                    "\n".join(cfgs)
                )

                logger.info(
                    f"💾 Saved "
                    f"{len(cfgs)} "
                    f"for {cc}"
                )

            else:
                others.extend(cfgs)

        except Exception as e:
            logger.warning(
                f"⚠️ Save fail "
                f"{cc}: {e}"
            )

    # ==========================
    # SAVE OTHERS
    # ==========================
    try:
        if others:

            file_path = os.path.join(
                root_path,
                "configs_others.txt"
            )

            atomic_write(
                file_path,
                "\n".join(others)
            )

            logger.info(
                f"💾 Saved "
                f"{len(others)} "
                f"in configs_others.txt"
            )

    except Exception as e:
        logger.warning(
            f"⚠️ Save others "
            f"failed: {e}"
        )


# ==========================================================
# STATS
# ==========================================================
def log_stats(
    all_configs,
    country_map
):
    """
    Better logging
    """

    found = sorted(
        IMPORTANT_COUNTRIES
        & set(country_map.keys())
    )

    logger.info(
        f"🌍 Important countries: "
        f"{found}"
    )

    logger.info(
        f"📦 Total configs: "
        f"{len(all_configs)}"
    )


# ==========================================================
# FAIL SAFE WRAPPER
# ==========================================================
async def safe_disconnect(
    client
):
    try:
        await client.disconnect()
    except Exception:
        pass
        # ==========================================================
# TELEGRAM SCRAPER
# ==========================================================
async def scrape_channels(client):
    """
    Read telegram channels
    Preserve behavior
    """

    raw_configs = []
    sub_links = []

    total_channels = len(CHANNELS)

    logger.info(
        f"📡 Reading "
        f"{total_channels} channels"
    )

    for idx, ch in enumerate(
        CHANNELS,
        start=1
    ):

        logger.info(
            f"📌 [{idx}/{total_channels}] "
            f"Reading channel: {ch}"
        )

        count = 0

        try:
            entity = await asyncio.wait_for(
                client.get_entity(ch),
                timeout=20
            )

            async for msg in client.iter_messages(
                entity,
                limit=CHANNEL_MESSAGE_LIMIT
            ):

                try:
                    if not msg.message:
                        continue

                    text = msg.message

                    # ----------------------
                    # subscription urls
                    # ----------------------
                    found_links = (
                        SUB_PATTERN.findall(text)
                    )

                    if found_links:
                        sub_links.extend(
                            found_links
                        )

                    # ----------------------
                    # configs
                    # ----------------------
                    configs = (
                        extract_configs(text)
                    )

                    if configs:
                        raw_configs.extend(
                            configs
                        )

                    count += 1

                    # anti flood
                    if count % 30 == 0:
                        await asyncio.sleep(
                            0.4
                        )

                except Exception as e:
                    logger.warning(
                        f"⚠️ Message parse "
                        f"error ({ch}): {e}"
                    )

            logger.info(
                f"📥 Fetched "
                f"{count} messages "
                f"from {ch}"
            )

        except FloodWaitError as e:

            wait_time = (
                e.seconds + 2
            )

            logger.warning(
                f"⏳ FloodWait "
                f"{wait_time}s "
                f"in {ch}"
            )

            await asyncio.sleep(
                wait_time
            )

        except asyncio.TimeoutError:

            logger.warning(
                f"⚠️ Timeout "
                f"in {ch}"
            )

        except Exception as e:

            logger.warning(
                f"⚠️ Channel fail "
                f"{ch}: {e}"
            )

        # keep behavior stable
        await asyncio.sleep(0.8)

    # dedupe urls
    sub_links = (
        dedupe_preserve_order(
            sub_links
        )
    )

    logger.info(
        f"🌐 Subscription links: "
        f"{len(sub_links)}"
    )

    logger.info(
        f"📦 Raw configs: "
        f"{len(raw_configs)}"
    )

    return raw_configs, sub_links


# ==========================================================
# SUBSCRIPTION PROCESSOR
# ==========================================================
def process_subscription_configs(
    sub_links
):
    """
    Parallel subscription fetch
    """

    try:
        if not sub_links:
            return []

        logger.info(
            "🌐 Processing "
            "subscriptions..."
        )

        results = (
            fetch_subscriptions_parallel(
                sub_links
            )
        )

        logger.info(
            f"📥 Subscription "
            f"configs: "
            f"{len(results)}"
        )

        return results

    except Exception as e:

        logger.warning(
            f"⚠️ Subscription "
            f"processing failed: {e}"
        )

        return []


# ==========================================================
# TELEGRAM LOGIN
# ==========================================================
async def create_client():
    """
    Create telegram client safely
    """

    client = TelegramClient(
        StringSession(
            SESSION_STRING
        ),
        API_ID,
        API_HASH
    )

    try:
        await asyncio.wait_for(
            client.connect(),
            timeout=30
        )

        authorized = (
            await client
            .is_user_authorized()
        )

        if not authorized:

            raise RuntimeError(
                "SESSION NOT AUTHORIZED"
            )

        logger.info(
            "✅ Login successful!"
        )

        return client

    except Exception as e:

        logger.error(
            f"❌ Login failed: {e}"
        )

        await safe_disconnect(
            client
        )

        return None


# ==========================================================
# CONFIG PROCESSOR
# ==========================================================
def process_configs(
    raw_configs,
    sub_configs
):
    """
    Keep behavior same
    but cleaner + safer
    """

    logger.info(
        "🧹 Processing configs..."
    )

    combined = (
        raw_configs
        + sub_configs
    )

    combined = sanitize_configs(
        combined
    )

    combined = dedupe_configs(
        combined
    )

    logger.info(
        f"📦 Final configs: "
        f"{len(combined)}"
    )

    return combined
    # ==========================================================
# MAIN
# ==========================================================
async def main():
    """
    Production main
    Keep current behavior
    Faster + safer
    """

    start_time = time.time()

    logger.info(
        "🚀 SCRAPER STARTED "
        "(USER MODE)"
    )

    load_country_cache()

    client = None

    try:
        # ==================================
        # LOGIN
        # ==================================
        client = await create_client()

        if not client:
            logger.error(
                "❌ Could not create client"
            )
            return

        # ==================================
        # SCRAPE CHANNELS
        # ==================================
        raw_configs, sub_links = (
            await scrape_channels(
                client
            )
        )

        # ==================================
        # SUBSCRIPTIONS
        # ==================================
        sub_configs = (
            process_subscription_configs(
                sub_links
            )
        )

        # ==================================
        # PROCESS CONFIGS
        # ==================================
        all_configs = process_configs(
            raw_configs,
            sub_configs
        )

        # ==================================
        # SAVE MAIN FILE
        # ==================================
        configs_file = os.path.join(
            ROOT_DIR,
            "configs.txt"
        )

        atomic_write(
            configs_file,
            "\n".join(all_configs)
        )

        logger.info(
            f"💾 Saved "
            f"{len(all_configs)} "
            f"to configs.txt"
        )

        # ==================================
        # COUNTRY DETECTION
        # ==================================
        logger.info(
            "🌍 Starting "
            "country detection..."
        )

        country_map = (
            batch_get_countries(
                all_configs
            )
        )

        # ==================================
        # SAVE COUNTRY FILES
        # ==================================
        save_country_files(
            ROOT_DIR,
            country_map
        )

        # ==================================
        # SAVE CACHE
        # ==================================
        save_country_cache()

        # ==================================
        # STATS
        # ==================================
        log_stats(
            all_configs,
            country_map
        )

        elapsed = round(
            time.time()
            - start_time,
            2
        )

        logger.info(
            f"🏁 SCRAPER "
            f"COMPLETED "
            f"SUCCESSFULLY "
            f"in {elapsed}s"
        )

    except Exception as e:

        logger.exception(
            f"❌ Fatal scraper error: "
            f"{e}"
        )

    finally:

        if client:
            await safe_disconnect(
                client
            )

        try:
            session.close()
        except Exception:
            pass


# ==========================================================
# ENTRYPOINT
# ==========================================================
if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        logger.warning(
            "⚠️ Interrupted"
        )

    except Exception as e:

        logger.exception(
            f"❌ Crash: {e}"
        )
        
