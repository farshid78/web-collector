# ==========================================================
# SCRAPER.PY (PART 1/3)
# Production Grade Telegram Config Scraper
# ==========================================================

import os
import re
import json
import time
import base64
import socket
import asyncio
import logging
import tempfile

from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
    Set
)

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

import requests

from dotenv import (
    load_dotenv
)

from telethon import (
    TelegramClient
)

from telethon.sessions import (
    StringSession
)

from telethon.errors import (
    FloodWaitError
)

# ==========================================================
# LOAD ENV
# ==========================================================

load_dotenv()

API_ID = int(
    os.getenv(
        "API_ID",
        "0"
    )
)

API_HASH = os.getenv(
    "API_HASH",
    ""
)

SESSION_STRING = os.getenv(
    "SESSION_STRING",
    ""
)

# ==========================================================
# ENV VALIDATION
# ==========================================================

if not API_ID:
    raise RuntimeError(
        "API_ID missing"
    )

if not API_HASH:
    raise RuntimeError(
        "API_HASH missing"
    )

if not SESSION_STRING:
    raise RuntimeError(
        "SESSION_STRING missing"
    )

# ==========================================================
# PATHS
# ==========================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

SCRAPER_DIR = (
    ROOT_DIR
    / "scraper"
)

STATE_DIR = (
    ROOT_DIR
    / "state"
)

OUTPUT_DIR = (
    ROOT_DIR
    / "output"
)

LOGS_DIR = (
    ROOT_DIR
    / "logs"
)

CHANNELS_FILE = (
    SCRAPER_DIR
    / "channels.json"
)

COUNTRY_CACHE_FILE = (
    STATE_DIR
    / "country_cache.json"
)

MAIN_CONFIG_FILE = (
    OUTPUT_DIR
    / "configs.txt"
)

SUBSCRIPTION_FILE = (
    OUTPUT_DIR
    / "subscription_links.txt"
)

# ساخت پوشه‌ها
for directory in [
    OUTPUT_DIR,
    STATE_DIR,
    LOGS_DIR
]:
    directory.mkdir(
        exist_ok=True
    )

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
    handlers=[
        logging.FileHandler(
            LOGS_DIR
            / "scraper.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(
    "SCRAPER"
)

# ==========================================================
# SETTINGS
# ==========================================================

THREAD_POOL_WORKERS = 20

CHANNEL_MESSAGE_LIMIT = 100

HTTP_TIMEOUT = 5

MAX_SUB_LINKS = 80

CACHE_TTL_DAYS = 14

CACHE_TTL_SECONDS = (
    CACHE_TTL_DAYS
    * 86400
)

REQUEST_RETRY = 3

TELEGRAM_DELAY = 0.7

IMPORTANT_COUNTRIES = {
    "IR",
    "TR",
    "US",
    "DE",
    "NL",
    "FI",
    "SG",
    "AE"
}
# ==========================================================
# COUNTRY FILTER SETTINGS
# ==========================================================

# ساخت فایل مستقل
MIN_COUNTRY_CONFIGS = 50

PROJECT_SUBSCRIPTION_URL = (
    "https://raw."
    "githubusercontent.com/"
    "farshid78/"
    "web-collector/"
    "main/output/"
    "configs.txt"
)

# ==========================================================
# CONFIG REGEX
# ==========================================================

CONFIG_REGEX = re.compile(
    r"(vmess://[^\s]+)"
    r"|"
    r"(vless://[^\s]+)"
    r"|"
    r"(trojan://[^\s]+)"
    r"|"
    r"(ss://[^\s]+)",
    re.IGNORECASE
)

SUB_REGEX = re.compile(
    r"https?://[^\s]+"
    r"(?:"
    r"\.txt|"
    r"/sub[^\s]*|"
    r"subscription[^\s]*"
    r")",
    re.IGNORECASE
)

# ==========================================================
# HTTP SESSION
# ==========================================================

session = requests.Session()

adapter = (
    requests.adapters
    .HTTPAdapter(
        pool_connections=50,
        pool_maxsize=50
    )
)

session.mount(
    "http://",
    adapter
)

session.mount(
    "https://",
    adapter
)

session.headers.update({
    "User-Agent":
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64)"
})

# ==========================================================
# HELPERS
# ==========================================================

def atomic_write(
    path: str,
    content: str
):
    """
    ذخیره اتمیک فایل
    جلوگیری از خراب شدن فایل
    """

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            delete=False,
            encoding="utf-8"
        ) as temp_file:

            temp_file.write(
                content
            )

            temp_name = (
                temp_file.name
            )

        os.replace(
            temp_name,
            path
        )

    except Exception as e:

        logger.error(
            f"Atomic write "
            f"failed: {e}"
        )


def dedupe_preserve_order(
    items: List[str]
) -> List[str]:
    """
    حذف duplicate
    بدون از دست رفتن ترتیب
    """

    seen: Set[str] = set()

    output = []

    for item in items:

        if (
            item
            and
            item not in seen
        ):
            seen.add(item)

            output.append(
                item
            )

    return output


def normalize_config(
    config: str
) -> str:
    """
    normalize config
    """

    if not config:
        return ""

    return (
        config
        .strip()
        .replace(
            "\r",
            ""
        )
    )


def safe_request(
    url: str,
    timeout: int = HTTP_TIMEOUT,
    retries: int = REQUEST_RETRY
) -> Optional[requests.Response]:
    """
    request مقاوم
    """

    for attempt in range(
        retries
    ):

        try:

            response = (
                session.get(
                    url,
                    timeout=timeout
                )
            )

            if (
                response.status_code
                == 200
            ):
                return response

        except Exception:
            pass

        sleep_time = (
            0.7
            *
            (
                attempt + 1
            )
        )

        time.sleep(
            sleep_time
        )

    return None


# ==========================================================
# CHANNEL LOADER
# ==========================================================

def load_channels() -> List[str]:
    """
    load channels.json
    """

    try:

        with open(
            CHANNELS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        channels = (
            data.get(
                "channels",
                []
            )
        )

        logger.info(
            f"📡 Channels="
            f"{len(channels)}"
        )

        return channels

    except Exception as e:

        logger.error(
            f"Channel load "
            f"failed: {e}"
        )

        return []
    # ==========================================================
# SCRAPER.PY (PART 2/3)
# Country Cache + Extraction + Country Detection
# + Subscription Fetch
# ==========================================================

# ==========================================================
# COUNTRY CACHE
# ==========================================================

country_cache: Dict[
    str,
    Dict
] = {}


def load_country_cache():
    """
    لود cache کشورها
    با TTL
    """

    global country_cache

    try:

        if not (
            COUNTRY_CACHE_FILE
            .exists()
        ):

            country_cache = {}

            return

        with open(
            COUNTRY_CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            raw_data = json.load(
                file
            )

        now = time.time()

        cleaned = {}

        for host, info in (
            raw_data.items()
        ):

            try:

                timestamp = (
                    info.get(
                        "ts",
                        0
                    )
                )

                if (
                    now
                    - timestamp
                    <
                    CACHE_TTL_SECONDS
                ):

                    cleaned[
                        host
                    ] = info

            except Exception:
                pass

        country_cache = (
            cleaned
        )

        logger.info(
            f"🌍 Cache="
            f"{len(country_cache)}"
        )

    except Exception as e:

        logger.warning(
            f"Cache load "
            f"failed: {e}"
        )


def save_country_cache():
    """
    ذخیره cache
    """

    try:

        atomic_write(
            str(
                COUNTRY_CACHE_FILE
            ),
            json.dumps(
                country_cache,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception as e:

        logger.warning(
            f"Cache save "
            f"failed: {e}"
        )


# ==========================================================
# CONFIG EXTRACTION
# ==========================================================

def extract_configs(
    text: str
) -> List[str]:
    """
    استخراج config
    """

    if not text:
        return []

    try:

        matches = (
            CONFIG_REGEX.findall(
                text
            )
        )

        results = []

        for match in matches:

            for item in match:

                if item:

                    normalized = (
                        normalize_config(
                            item
                        )
                    )

                    if normalized:

                        results.append(
                            normalized
                        )

        return results

    except Exception as e:

        logger.warning(
            f"Extract config "
            f"failed: {e}"
        )

        return []


def extract_sub_links(
    text: str
) -> List[str]:
    """
    استخراج subscription url
    """

    if not text:
        return []

    try:

        found = (
            SUB_REGEX.findall(
                text
            )
        )

        return (
            dedupe_preserve_order(
                found
            )
        )

    except Exception:

        return []


# ==========================================================
# HOST EXTRACTION
# ==========================================================

def extract_host(
    config: str
) -> Optional[str]:
    """
    استخراج host
    """

    try:

        if config.startswith(
            "vmess://"
        ):

            raw = config[8:]

            padding = (
                len(raw)
                % 4
            )

            if padding:

                raw += (
                    "="
                    *
                    (
                        4
                        - padding
                    )
                )

            decoded = (
                base64
                .b64decode(raw)
                .decode(
                    "utf-8",
                    errors="ignore"
                )
            )

            payload = (
                json.loads(
                    decoded
                )
            )

            return (
                payload.get(
                    "add"
                )
                or
                payload.get(
                    "host"
                )
                or
                payload.get(
                    "server"
                )
            )

        _, rest = (
            config.split(
                "://",
                1
            )
        )

        if "@" in rest:

            rest = (
                rest.split(
                    "@",
                    1
                )[1]
            )

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
# COUNTRY DETECTION
# ==========================================================

def resolve_host(
    host: str
) -> Optional[str]:
    """
    resolve hostname
    """

    try:

        if not host:
            return None

        host = (
            host.strip()
        )

        # IP
        if (
            host.replace(
                ".",
                ""
            )
            .isdigit()
        ):
            return host

        return (
            socket
            .gethostbyname(
                host
            )
        )

    except Exception:

        return None


def get_country_code(
    host: str
) -> str:
    """
    دریافت کشور
    """

    if not host:

        return "UNKNOWN"

    host = host.strip()

    cached = (
        country_cache
        .get(host)
    )

    if cached:

        return (
            cached.get(
                "country",
                "UNKNOWN"
            )
        )

    try:

        ip = (
            resolve_host(
                host
            )
        )

        if not ip:

            country_code = (
                "UNKNOWN"
            )

        else:

            url = (
                "http://"
                "ip-api.com/"
                "json/"
                f"{ip}"
                "?fields="
                "countryCode"
            )

            response = (
                safe_request(
                    url,
                    timeout=4,
                    retries=2
                )
            )

            if response:

                try:

                    country_code = (
                        response
                        .json()
                        .get(
                            "countryCode",
                            "UNKNOWN"
                        )
                    )

                except Exception:

                    country_code = (
                        "UNKNOWN"
                    )

            else:

                country_code = (
                    "UNKNOWN"
                )

    except Exception:

        country_code = (
            "UNKNOWN"
        )

    country_cache[
        host
    ] = {
        "country":
        country_code,
        "ts":
        int(
            time.time()
        )
    }

    return country_code


def batch_get_countries(
    configs: List[str]
) -> Dict[
    str,
    List[str]
]:
    """
    تشخیص کشور
    با parallel execution
    """

    result = {}

    if not configs:

        return result

    host_to_configs = {}

    for config in configs:

        try:

            host = (
                extract_host(
                    config
                )
            )

            if not host:

                host = (
                    "UNKNOWN"
                )

            host_to_configs\
                .setdefault(
                    host,
                    []
                )\
                .append(
                    config
                )

        except Exception:
            continue

    unique_hosts = list(
        host_to_configs.keys()
    )

    total = len(
        unique_hosts
    )

    logger.info(
        f"🌍 Hosts="
        f"{total}"
    )

    host_country_map = {}

    with ThreadPoolExecutor(
        max_workers=
        THREAD_POOL_WORKERS
    ) as executor:

        futures = {

            executor.submit(
                get_country_code,
                host
            ): host

            for host
            in unique_hosts
        }

        completed = 0

        for future in (
            as_completed(
                futures
            )
        ):

            host = futures[
                future
            ]

            try:

                cc = (
                    future
                    .result()
                )

                if not cc:

                    cc = (
                        "UNKNOWN"
                    )

            except Exception:

                cc = (
                    "UNKNOWN"
                )

            host_country_map[
                host
            ] = cc

            completed += 1

            if (
                completed % 50
                == 0
                or
                completed
                == total
            ):

                logger.info(
                    f"🌍 "
                    f"{completed}"
                    f"/"
                    f"{total}"
                )

    for host, configs_list in (
        host_to_configs.items()
    ):

        country = (
            host_country_map
            .get(
                host,
                "UNKNOWN"
            )
        )

        result\
            .setdefault(
                country,
                []
            )\
            .extend(
                configs_list
            )

    return result


# ==========================================================
# SUBSCRIPTION FETCH
# ==========================================================

def fetch_subscription(
    url: str
) -> List[str]:
    """
    دانلود subscription
    """

    try:

        response = (
            safe_request(
                url,
                timeout=5,
                retries=2
            )
        )

        if not response:

            return []

        text = (
            response.text
        )

        configs = (
            extract_configs(
                text
            )
        )

        return configs

    except Exception as e:

        logger.warning(
            f"Subscription "
            f"failed: {e}"
        )

        return []


def fetch_subscriptions_parallel(
    urls: List[str]
) -> List[str]:
    """
    parallel fetch
    """

    urls = (
        dedupe_preserve_order(
            urls
        )[
            :MAX_SUB_LINKS
        ]
    )

    if not urls:

        return []

    logger.info(
        f"🌐 Subs="
        f"{len(urls)}"
    )

    results = []

    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        futures = {

            executor.submit(
                fetch_subscription,
                url
            ): url

            for url
            in urls
        }

        for future in (
            as_completed(
                futures
            )
        ):

            try:

                configs = (
                    future.result()
                )

                if configs:

                    results.extend(
                        configs
                    )

            except Exception:
                pass

    return (
        dedupe_preserve_order(
            results
        )
    )
# ==========================================================
# SCRAPER.PY (PART 3/3)
# Telegram Scraper + Save Output + Cleanup + Main
# ==========================================================

# ==========================================================
# TELEGRAM SCRAPER
# ==========================================================

async def scrape_channels(
    client: TelegramClient
):
    """
    اسکرپ کانال‌ها
    """

    channels = (
        load_channels()
    )

    raw_configs = []
    sub_links = []

    total = len(
        channels
    )

    logger.info(
        f"📡 Total Channels="
        f"{total}"
    )

    for index, channel in enumerate(
        channels,
        start=1
    ):

        logger.info(
            f"[{index}/{total}] "
            f"{channel}"
        )

        try:

            entity = await (
                asyncio.wait_for(
                    client.get_entity(
                        channel
                    ),
                    timeout=20
                )
            )

            async for message in (
                client.iter_messages(
                    entity,
                    limit=
                    CHANNEL_MESSAGE_LIMIT
                )
            ):

                try:

                    text = (
                        message.message
                    )

                    if not text:
                        continue

                    raw_configs.extend(
                        extract_configs(
                            text
                        )
                    )

                    sub_links.extend(
                        extract_sub_links(
                            text
                        )
                    )

                except Exception:
                    pass

            await asyncio.sleep(
                TELEGRAM_DELAY
            )

        except (
            FloodWaitError
        ) as e:

            wait_time = (
                e.seconds + 2
            )

            logger.warning(
                f"FloodWait "
                f"{wait_time}s"
            )

            await asyncio.sleep(
                wait_time
            )

        except Exception as e:

            logger.warning(
                f"{channel}: {e}"
            )

    return (
        dedupe_preserve_order(
            raw_configs
        ),
        dedupe_preserve_order(
            sub_links
        )
    )


# ==========================================================
# SAVE COUNTRY FILES
# ==========================================================
def save_country_files(country_map):
    """
    فایل کشورهایی که کمتر از threshold هستند
    ساخته نمی‌شوند و داخل others می‌روند.
    """

    others = []

    for cc, cfgs in country_map.items():

        try:

            cfgs = dedupe_preserve_order(cfgs)

            total_configs = len(cfgs)

            # --------------------------------
            # کشورهای مهم
            # --------------------------------
            if cc in IMPORTANT_COUNTRIES:

                # اگر کمتر از حداقل بود
                if total_configs < MIN_COUNTRY_CONFIGS:

                    logger.info(
                        f"⏭️ skip {cc} "
                        f"({total_configs} < "
                        f"{MIN_COUNTRY_CONFIGS})"
                    )

                    file_path = (
                        OUTPUT_DIR /
                        f"configs_{cc}.txt"
                    )

                    # حذف فایل قدیمی اگر وجود دارد
                    if file_path.exists():

                        try:

                            file_path.unlink()

                            logger.info(
                                f"🗑️ removed stale "
                                f"{file_path.name}"
                            )

                        except Exception as e:

                            logger.warning(
                                f"failed remove "
                                f"{file_path.name}: {e}"
                            )

                    others.extend(cfgs)
                    continue

                # ذخیره فایل کشور
                file_path = (
                    OUTPUT_DIR /
                    f"configs_{cc}.txt"
                )

                atomic_write(
                    str(file_path),
                    "\n".join(cfgs)
                )

                logger.info(
                    f"💾 {cc}="
                    f"{total_configs}"
                )

            else:
                others.extend(cfgs)

        except Exception as e:

            logger.warning(
                f"save fail "
                f"{cc}: {e}"
            )

    # --------------------------------
    # others
    # --------------------------------

    others = dedupe_preserve_order(
        others
    )

    others_file = (
        OUTPUT_DIR /
        "configs_others.txt"
    )

    if others:

        atomic_write(
            str(others_file),
            "\n".join(others)
        )

        logger.info(
            f"💾 others="
            f"{len(others)}"
        )

    else:
        # اگر خالی بود فایل قبلی حذف شود
        if others_file.exists():

            try:

                others_file.unlink()

                logger.info(
                    "🗑️ removed "
                    "configs_others.txt"
                )

            except Exception as e:

                logger.warning(
                    f"remove others "
                    f"failed: {e}"
                )
# ==========================================================
# CLEANUP FILES
# ==========================================================

def cleanup_stale_files():
    """
    حذف فایل‌های اضافی
    bundle_info.txt حذف شد
    project_subscription.txt حذف شد
    """

    desired = {
     "configs.txt",

    "subscription_links.txt",

    "configs_others.txt",

    "configs_IR.txt",

    "configs_TR.txt",

    "configs_US.txt",

    "configs_DE.txt",

    "configs_NL.txt",

    "configs_FI.txt",

    "configs_SG.txt",

    "configs_AE.txt"
    }




    try:

        for file in (
            OUTPUT_DIR.glob("*")
        ):

            try:

                if (
                    file.is_file()
                    and
                    file.name
                    not in desired
                ):

                    file.unlink()

                    logger.info(
                        f"🧹 Removed "
                        f"{file.name}"
                    )

            except Exception:
                pass

    except Exception as e:

        logger.warning(
            f"Cleanup failed: "
            f"{e}"
        )


# ==========================================================
# CREATE TELEGRAM CLIENT
# ==========================================================

async def create_client():
    """
    ساخت Telegram client
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

        authorized = await (
            client
            .is_user_authorized()
        )

        if not authorized:

            raise RuntimeError(
                "Session not "
                "authorized"
            )

        logger.info(
            "Telegram "
            "connected"
        )

        return client

    except Exception as e:

        logger.exception(
            f"Client Error: "
            f"{e}"
        )

        try:
            await (
                client
                .disconnect()
            )
        except Exception:
            pass

        return None


# ==========================================================
# MAIN
# ==========================================================

async def main():
    """
    Main Production Flow
    """

    logger.info(
        "🚀 Scraper Starting..."
    )

    start_time = (
        time.time()
    )

    load_country_cache()

    cleanup_stale_files()

    client = None

    try:

        # ======================================
        # CONNECT
        # ======================================

        client = await (
            create_client()
        )

        if not client:
            return

        # ======================================
        # SCRAPE CHANNELS
        # ======================================

        raw_configs, sub_links = (
            await scrape_channels(
                client
            )
        )

        logger.info(
            f"📦 Raw="
            f"{len(raw_configs)}"
        )

        logger.info(
            f"🌐 Links="
            f"{len(sub_links)}"
        )

        # ======================================
        # SAVE LINKS
        # ======================================

        atomic_write(
            str(
                SUBSCRIPTION_FILE
            ),
            "\n".join(
                sub_links
            )
        )

        # ======================================
        # FETCH SUBSCRIPTIONS
        # ======================================

        subscription_configs = (
            fetch_subscriptions_parallel(
                sub_links
            )
        )

        logger.info(
            f"📥 Subs="
            f"{len(subscription_configs)}"
        )

        # ======================================
        # MERGE CONFIGS
        # ======================================

        all_configs = (
            dedupe_preserve_order(
                raw_configs
                +
                subscription_configs
            )
        )

        all_configs = [

            normalize_config(
                item
            )

            for item
            in all_configs

            if item
        ]

        logger.info(
            f"📦 Total="
            f"{len(all_configs)}"
        )

        # ======================================
        # SAVE MAIN FILE
        # ======================================

        atomic_write(
            str(
                MAIN_CONFIG_FILE
            ),
            "\n".join(
                all_configs
            )
        )

        # ======================================
        # COUNTRY DETECTION
        # ======================================

        logger.info(
            "🌍 Country "
            "Detection..."
        )

        country_map = (
            batch_get_countries(
                all_configs
            )
        )

        save_country_files(
            country_map
        )

        # ======================================
        # SAVE CACHE
        # ======================================

        save_country_cache()

        elapsed = round(
            time.time()
            - start_time,
            2
        )

        logger.info(
            f"🏁 Finished "
            f"in {elapsed}s"
        )

    except Exception as e:

        logger.exception(
            f"Fatal Error: "
            f"{e}"
        )

    finally:

        try:

            if client:

                await (
                    client
                    .disconnect()
                )

        except Exception:
            pass

        try:

            session.close()

        except Exception:
            pass

        logger.info(
            "Graceful Shutdown"
        )


# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.warning(
            "Stopped "
            "Manually"
        )

    except RuntimeError as e:

        logger.exception(
            f"Runtime "
            f"Error: {e}"
        )

    except Exception as e:

        logger.exception(
            f"Crash: {e}"
        )

    finally:

        logger.info(
            "Cleanup Done"
        )
