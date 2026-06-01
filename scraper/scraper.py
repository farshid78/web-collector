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
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)

import requests
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import (
    StringSession
)
from telethon.errors import (
    FloodWaitError
)

# ==========================================================
# ENV
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

STATE_DIR.mkdir(
    exist_ok=True
)

OUTPUT_DIR.mkdir(
    exist_ok=True
)

CHANNELS_FILE = (
    SCRAPER_DIR
    / "channels.json"
)

COUNTRY_CACHE_FILE = (
    STATE_DIR
    / "country_cache.json"
)

SUBSCRIPTION_FILE = (
    OUTPUT_DIR
    / "subscription_links.txt"
)

PROJECT_SUB_FILE = (
    OUTPUT_DIR
    / "project_subscription.txt"
)

BUNDLE_INFO_FILE = (
    OUTPUT_DIR
    / "bundle_info.txt"
)

MAIN_CONFIG_FILE = (
    OUTPUT_DIR
    / "configs.txt"
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
    )
)

logger = logging.getLogger(
    "SCRAPER"
)

# ==========================================================
# SETTINGS
# ==========================================================

THREAD_POOL_WORKERS = 16
HTTP_TIMEOUT = 3
CHANNEL_MESSAGE_LIMIT = 90
MAX_SUB_LINKS = 50

CACHE_TTL_DAYS = 14
CACHE_TTL_SECONDS = (
    CACHE_TTL_DAYS
    * 86400
)

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

STARTERS = [
    "vmess://",
    "vless://",
    "trojan://",
    "ss://"
]

PROJECT_SUB_LINK = (
    "https://raw."
    "githubusercontent.com/"
    "farshid78/"
    "web-collector/"
    "main/output/"
    "configs.txt"
)

# ==========================================================
# REGEX EXTRACTION (S1)
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
    r"(?:\.txt|"
    r"/sub[^\s]*|"
    r"subscription[^\s]*)",
    re.IGNORECASE
)

# ==========================================================
# HTTP SESSION
# ==========================================================

session = requests.Session()

adapter = (
    requests.adapters
    .HTTPAdapter(
        pool_connections=25,
        pool_maxsize=25
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
    "Mozilla/5.0"
})

# ==========================================================
# HELPERS
# ==========================================================

def atomic_write(
    path,
    content
):

    try:

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8"
        ) as tf:

            tf.write(content)

            temp_name = (
                tf.name
            )

        os.replace(
            temp_name,
            path
        )

    except Exception as e:

        logger.error(
            f"atomic write "
            f"failed: {e}"
        )


def dedupe_preserve_order(
    items
):

    seen = set()
    output = []

    for item in items:

        if (
            item
            not in seen
        ):
            seen.add(
                item
            )

            output.append(
                item
            )

    return output


def normalize_config(
    cfg
):

    if not cfg:
        return ""

    return (
        cfg.strip()
        .replace(
            "\r",
            ""
        )
    )


def safe_request(
    url,
    timeout=
    HTTP_TIMEOUT,
    retries=3
):

    for attempt in range(
        retries
    ):

        try:

            response = (
                session.get(
                    url,
                    timeout=
                    timeout
                )
            )

            if (
                response
                .status_code
                == 200
            ):

                return response

        except Exception:
            pass

        time.sleep(
            0.7
            *
            (
                attempt + 1
            )
        )

    return None

# ==========================================================
# CHANNELS.JSON (F2)
# ==========================================================

def load_channels():

    try:

        with open(
            CHANNELS_FILE,
            "r",
            encoding=
            "utf-8"
        ) as f:

            data = (
                json.load(
                    f
                )
            )

        channels = (
            data.get(
                "channels",
                []
            )
        )

        logger.info(
            f"📡 channels="
            f"{len(channels)}"
        )

        return channels

    except Exception as e:

        logger.error(
            f"channels load "
            f"failed: {e}"
        )

        return []

# ==========================================================
# TTL CACHE (S3)
# ==========================================================

country_cache = {}


def load_country_cache():

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
            encoding=
            "utf-8"
        ) as f:

            data = (
                json.load(
                    f
                )
            )

        now = (
            time.time()
        )

        cleaned = {}

        for host, info in (
            data.items()
        ):

            try:

                ts = (
                    info.get(
                        "ts",
                        0
                    )
                )

                if (
                    now - ts
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
            f"🌍 cache="
            f"{len(country_cache)}"
        )

    except Exception as e:

        logger.warning(
            f"cache load "
            f"fail: {e}"
        )


def save_country_cache():

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
            f"cache save "
            f"fail: {e}"
        )
        # ==========================================================
# CONFIG EXTRACTION (S1)
# ==========================================================

def extract_configs(text):
    """
    Regex based extraction
    Better than line split
    """

    if not text:
        return []

    try:

        matches = (
            CONFIG_REGEX.findall(
                text
            )
        )

        configs = []

        for match in matches:

            for item in match:

                if item:

                    cfg = (
                        normalize_config(
                            item
                        )
                    )

                    if cfg:
                        configs.append(
                            cfg
                        )

        return configs

    except Exception as e:

        logger.warning(
            f"extract fail: "
            f"{e}"
        )

        return []


def extract_sub_links(text):

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

def extract_host(cfg):

    try:

        if cfg.startswith(
            "vmess://"
        ):

            raw = cfg[8:]

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
                .b64decode(
                    raw
                )
                .decode(
                    "utf-8",
                    errors=
                    "ignore"
                )
            )

            data = (
                json.loads(
                    decoded
                )
            )

            return (
                data.get(
                    "add"
                )
                or
                data.get(
                    "host"
                )
                or
                data.get(
                    "server"
                )
            )

        _, rest = (
            cfg.split(
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

def resolve_host(host):

    try:

        if not host:
            return None

        host = (
            host.strip()
        )

        if (
            host
            .replace(
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
    host
):

    if not host:
        return "UNKNOWN"

    host = (
        host.strip()
    )

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

            cc = (
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

                    cc = (
                        response
                        .json()
                        .get(
                            "countryCode",
                            "UNKNOWN"
                        )
                    )

                except Exception:

                    cc = (
                        "UNKNOWN"
                    )

            else:

                cc = (
                    "UNKNOWN"
                )

    except Exception:

        cc = "UNKNOWN"

    country_cache[
        host
    ] = {
        "country":
        cc,
        "ts":
        int(
            time.time()
        )
    }

    return cc


def batch_get_countries(
    configs
):
    """
    Fast country detection
    resolve unique hosts only
    """

    country_map = {}

    if not configs:
        return country_map

    # ==================================
    # BUILD UNIQUE HOST MAP
    # ==================================

    host_to_configs = {}

    for cfg in configs:

        try:

            host = extract_host(
                cfg
            )

            if not host:
                host = "UNKNOWN"

            host_to_configs\
                .setdefault(
                    host,
                    []
                )\
                .append(cfg)

        except Exception:
            continue

    unique_hosts = list(
        host_to_configs.keys()
    )

    total_hosts = len(
        unique_hosts
    )

    logger.info(
        f"🌍 unique hosts="
        f"{total_hosts}"
    )

    host_country_map = {}

    # ==================================
    # PARALLEL LOOKUP
    # ==================================

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

        for future in as_completed(
            futures
        ):

            host = futures[
                future
            ]

            try:

                cc = future.result()

                if not cc:
                    cc = "UNKNOWN"

            except Exception:

                cc = "UNKNOWN"

            host_country_map[
                host
            ] = cc

            completed += 1

            if (
                completed % 50
                == 0
                or
                completed
                == total_hosts
            ):

                logger.info(
                    f"🌍 "
                    f"{completed}/"
                    f"{total_hosts}"
                )

    # ==================================
    # REBUILD COUNTRY MAP
    # ==================================

    for host, cfgs in (
        host_to_configs.items()
    ):

        cc = (
            host_country_map
            .get(
                host,
                "UNKNOWN"
            )
        )

        country_map\
            .setdefault(
                cc,
                []
            )\
            .extend(
                cfgs
            )

    return country_map

# ==========================================================
# SUBSCRIPTION FETCH
# ==========================================================

def fetch_subscription(
    url
):

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
            f"sub fail "
            f"{url}: "
            f"{e}"
        )

        return []


def fetch_subscriptions_parallel(
    urls
):

    urls = (
        dedupe_preserve_order(
            urls
        )[
            :MAX_SUB_LINKS
        ]
    )

    results = []

    if not urls:
        return results

    logger.info(
        f"🌐 subs="
        f"{len(urls)}"
    )

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

        for future in (
            as_completed(
                futures
            )
        ):

            try:

                result = (
                    future
                    .result()
                )

                if result:

                    results.extend(
                        result
                    )

            except Exception:
                pass

    return (
        dedupe_preserve_order(
            results
        )
    )

# ==========================================================
# TELEGRAM SCRAPER
# ==========================================================

async def scrape_channels(
    client
):

    channels = (
        load_channels()
    )

    raw_configs = []
    sub_links = []

    total = len(
        channels
    )

    logger.info(
        f"📡 channels="
        f"{total}"
    )

    for index, ch in enumerate(
        channels,
        start=1
    ):

        logger.info(
            f"[{index}/"
            f"{total}] "
            f"{ch}"
        )

        try:

            entity = (
                await asyncio
                .wait_for(
                    client
                    .get_entity(
                        ch
                    ),
                    timeout=20
                )
            )

            async for msg in (
                client
                .iter_messages(
                    entity,
                    limit=
                    CHANNEL_MESSAGE_LIMIT
                )
            ):

                try:

                    text = (
                        msg.message
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
                0.8
            )

        except (
            FloodWaitError
        ) as e:

            wait_time = (
                e.seconds
                + 2
            )

            logger.warning(
                f"floodwait "
                f"{wait_time}s"
            )

            await asyncio.sleep(
                wait_time
            )

        except Exception as e:

            logger.warning(
                f"{ch}: "
                f"{e}"
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
# SAVE OUTPUT FILES
# ==========================================================

def save_country_files(
    country_map
):

    others = []

    for cc, cfgs in (
        country_map.items()
    ):

        cfgs = (
            dedupe_preserve_order(
                cfgs
            )
        )

        try:

            if (
                cc
                in
                IMPORTANT_COUNTRIES
            ):

                file_path = (
                    OUTPUT_DIR
                    /
                    f"configs_"
                    f"{cc}.txt"
                )

                atomic_write(
                    str(
                        file_path
                    ),
                    "\n".join(
                        cfgs
                    )
                )

                logger.info(
                    f"💾 {cc}="
                    f"{len(cfgs)}"
                )

            else:

                others.extend(
                    cfgs
                )

        except Exception as e:

            logger.warning(
                f"save fail "
                f"{cc}: {e}"
            )

    others = (
        dedupe_preserve_order(
            others
        )
    )

    if others:

        atomic_write(
            str(
                OUTPUT_DIR
                /
                "configs_others.txt"
            ),
            "\n".join(
                others
            )
        )

# ==========================================================
# STALE CLEANUP (S4)
# ==========================================================

def cleanup_stale_files():

    desired = {
        "configs.txt",
        "configs_IR.txt",
        "configs_TR.txt",
        "configs_US.txt",
        "configs_DE.txt",
        "configs_NL.txt",
        "configs_FI.txt",
        "configs_SG.txt",
        "configs_AE.txt",
        "configs_others.txt",
        "subscription_links.txt",
        "project_subscription.txt",
        "bundle_info.txt"
    }

    try:

        for file in (
            OUTPUT_DIR
            .glob("*")
        ):

            if (
                file.is_file()
                and
                file.name
                not in desired
            ):

                try:

                    file.unlink()

                    logger.info(
                        f"🧹 removed "
                        f"{file.name}"
                    )

                except Exception:
                    pass

    except Exception as e:

        logger.warning(
            f"cleanup fail: "
            f"{e}"
        )

# ==========================================================
# TELEGRAM LOGIN
# ==========================================================

async def create_client():

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
                "session "
                "not authorized"
            )

        logger.info(
            "✅ telegram "
            "connected"
        )

        return client

    except Exception as e:

        logger.error(
            f"login fail: "
            f"{e}"
        )

        try:
            await client.disconnect()
        except Exception:
            pass

        return None

# ==========================================================
# MAIN
# ==========================================================

async def main():

    logger.info(
        "🚀 scraper "
        "started"
    )

    start_time = (
        time.time()
    )

    load_country_cache()

    cleanup_stale_files()

    client = None

    try:

        # ==========================
        # LOGIN
        # ==========================

        client = (
            await create_client()
        )

        if not client:
            return

        # ==========================
        # SCRAPE CHANNELS
        # ==========================

        raw_configs, sub_links = (
            await scrape_channels(
                client
            )
        )

        logger.info(
            f"📦 raw="
            f"{len(raw_configs)}"
        )

        logger.info(
            f"🌐 links="
            f"{len(sub_links)}"
        )

        # ==========================
        # SAVE SUB LINKS
        # ==========================

        atomic_write(
            str(
                SUBSCRIPTION_FILE
            ),
            "\n".join(
                sub_links
            )
        )

        # ==========================
        # FETCH SUBS
        # ==========================

        sub_configs = (
            fetch_subscriptions_parallel(
                sub_links
            )
        )

        logger.info(
            f"📥 subs="
            f"{len(sub_configs)}"
        )

        # ==========================
        # COMBINE
        # ==========================

        all_configs = (
            dedupe_preserve_order(
                raw_configs
                +
                sub_configs
            )
        )

        all_configs = [
            normalize_config(
                x
            )
            for x
            in all_configs
            if x
        ]

        logger.info(
            f"📦 total="
            f"{len(all_configs)}"
        )

        # ==========================
        # SAVE MAIN FILE
        # ==========================

        atomic_write(
            str(
                MAIN_CONFIG_FILE
            ),
            "\n".join(
                all_configs
            )
        )

        # ==========================
        # PROJECT SUB FILE
        # ==========================

        atomic_write(
            str(
                PROJECT_SUB_FILE
            ),
            PROJECT_SUB_LINK
        )

        # ==========================
        # COUNTRY DETECTION
        # ==========================

        logger.info(
            "🌍 country "
            "detecting..."
        )

        country_map = (
            batch_get_countries(
                all_configs
            )
        )

        save_country_files(
            country_map
        )

        # ==========================
        # BUNDLE INFO
        # ==========================

        bundle_info = (
            "WEB COLLECTOR\n"
            "================\n\n"
            f"Configs: "
            f"{len(all_configs)}\n"
            f"Subscription "
            f"Links: "
            f"{len(sub_links)}\n"
            f"Countries: "
            f"{len(country_map)}\n\n"
            "Project "
            "Subscription:\n"
            f"{PROJECT_SUB_LINK}\n\n"
            f"Updated UTC:\n"
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        atomic_write(
            str(
                BUNDLE_INFO_FILE
            ),
            bundle_info
        )

        # ==========================
        # SAVE CACHE
        # ==========================

        save_country_cache()

        elapsed = round(
            time.time()
            - start_time,
            2
        )

        logger.info(
            f"🏁 done "
            f"{elapsed}s"
        )

    except Exception as e:

        logger.exception(
            f"fatal: {e}"
        )

    finally:

        try:

            if client:

                await client.disconnect()

        except Exception:
            pass

        try:
            session.close()
        except Exception:
            pass

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
            "interrupted"
        )

    except Exception as e:

        logger.exception(
            f"crash: {e}"
        )
        