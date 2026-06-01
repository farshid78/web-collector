import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

import requests
from dotenv import load_dotenv

from telethon import (
    TelegramClient,
    events
)

from telethon.errors import (
    FloodWaitError,
    UserIsBlockedError,
    ChatWriteForbiddenError
)

# =====================================================
# ENV
# =====================================================

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

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
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

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN missing"
    )

# =====================================================
# PATHS
# =====================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

OUTPUT_DIR = (
    ROOT_DIR
    / "output"
)

STATE_DIR = (
    ROOT_DIR
    / "state"
)

LOGS_DIR = (
    ROOT_DIR
    / "logs"
)

STATE_DIR.mkdir(
    exist_ok=True
)

LOGS_DIR.mkdir(
    exist_ok=True
)

USERS_FILE = (
    ROOT_DIR
    / "users.json"
)

OFFSET_FILE = (
    STATE_DIR
    / "telegram_offset.json"
)

ANALYTICS_FILE = (
    STATE_DIR
    / "analytics.json"
)

# =====================================================
# LOGGING
# =====================================================

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
            / "bot.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(
    "BOT"
)

# =====================================================
# SETTINGS
# =====================================================

PARALLEL_USERS = 8
RETRY_COUNT = 3
REQUEST_TIMEOUT = 15
SEND_DELAY = 0.8

DESIRED_FILES = [
    "bundle_info.txt",
    "project_subscription.txt",
    "subscription_links.txt",
    "configs.txt",
    "configs_IR.txt",
    "configs_TR.txt",
    "configs_US.txt",
    "configs_DE.txt",
    "configs_NL.txt",
    "configs_FI.txt",
    "configs_SG.txt",
    "configs_AE.txt",
    "configs_others.txt"
]

# =====================================================
# USERS
# =====================================================

def load_users():

    try:

        if not USERS_FILE.exists():

            with open(
                USERS_FILE,
                "w",
                encoding=
                "utf-8"
            ) as f:

                json.dump(
                    [],
                    f
                )

            return []

        with open(
            USERS_FILE,
            "r",
            encoding=
            "utf-8"
        ) as f:

            data = (
                json.load(f)
            )

        users = []

        for uid in data:

            try:

                uid = int(uid)

                if uid not in users:
                    users.append(uid)

            except Exception:
                pass

        logger.info(
            f"👥 users="
            f"{len(users)}"
        )

        return users

    except Exception as e:

        logger.error(
            f"load users "
            f"fail: {e}"
        )

        return []


def save_users(users):

    try:

        users = sorted(
            list(
                dict.fromkeys(
                    int(x)
                    for x in users
                )
            )
        )

        with open(
            USERS_FILE,
            "w",
            encoding=
            "utf-8"
        ) as f:

            json.dump(
                users,
                f,
                indent=2
            )

    except Exception as e:

        logger.error(
            f"save users "
            f"fail: {e}"
        )

# =====================================================
# ANALYTICS (B4)
# =====================================================

def load_analytics():

    try:

        if not (
            ANALYTICS_FILE
            .exists()
        ):
            return {}

        with open(
            ANALYTICS_FILE,
            "r",
            encoding=
            "utf-8"
        ) as f:

            return json.load(f)

    except Exception:
        return {}


def save_analytics(
    success=0,
    failed=0,
    removed=0
):

    analytics = (
        load_analytics()
    )

    analytics[
        "last_run"
    ] = datetime.utcnow()\
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    analytics[
        "success"
    ] = (
        analytics.get(
            "success",
            0
        )
        + success
    )

    analytics[
        "failed"
    ] = (
        analytics.get(
            "failed",
            0
        )
        + failed
    )

    analytics[
        "removed"
    ] = (
        analytics.get(
            "removed",
            0
        )
        + removed
    )

    try:

        with open(
            ANALYTICS_FILE,
            "w",
            encoding=
            "utf-8"
        ) as f:

            json.dump(
                analytics,
                f,
                indent=2,
                ensure_ascii=False
            )

    except Exception:
        pass

# =====================================================
# OFFSET PERSISTENCE (B1)
# =====================================================

def load_offset():

    try:

        if not (
            OFFSET_FILE
            .exists()
        ):
            return 0

        with open(
            OFFSET_FILE,
            "r",
            encoding=
            "utf-8"
        ) as f:

            data = (
                json.load(f)
            )

        return int(
            data.get(
                "offset",
                0
            )
        )

    except Exception:
        return 0


def save_offset(
    offset
):

    try:

        with open(
            OFFSET_FILE,
            "w",
            encoding=
            "utf-8"
        ) as f:

            json.dump(
                {
                    "offset":
                    offset
                },
                f,
                indent=2
            )

    except Exception:
        pass
    # =====================================================
# TELEGRAM USER FETCH (B1)
# =====================================================

def get_users_from_telegram():
    """
    getUpdates with persistent offset
    """

    logger.info(
        "🔍 telegram users..."
    )

    users = []

    try:

        offset = (
            load_offset()
        )

        url = (
            "https://"
            "api.telegram.org/"
            f"bot{BOT_TOKEN}"
            "/getUpdates"
        )

        response = requests.get(
            url,
            params={
                "offset":
                offset,
                "timeout":
                10
            },
            timeout=
            REQUEST_TIMEOUT
        )

        if (
            response
            .status_code
            != 200
        ):

            logger.warning(
                f"bad status "
                f"{response.status_code}"
            )

            return []

        data = (
            response.json()
        )

        max_update_id = (
            offset
        )

        for update in (
            data.get(
                "result",
                []
            )
        ):

            try:

                update_id = (
                    update.get(
                        "update_id",
                        0
                    )
                )

                if (
                    update_id
                    >
                    max_update_id
                ):
                    max_update_id = (
                        update_id
                    )

                message = (
                    update.get(
                        "message",
                        {}
                    )
                )

                user = (
                    message.get(
                        "from",
                        {}
                    )
                )

                uid = (
                    user.get(
                        "id"
                    )
                )

                if uid:
                    users.append(
                        int(uid)
                    )

            except Exception:
                pass

        save_offset(
            max_update_id
            + 1
        )

        users = (
            list(
                dict.fromkeys(
                    users
                )
            )
        )

        logger.info(
            f"👥 telegram="
            f"{len(users)}"
        )

        return users

    except Exception as e:

        logger.error(
            f"getUpdates "
            f"fail: {e}"
        )

        return []

# =====================================================
# USER MERGE
# =====================================================

def get_all_users():

    file_users = (
        load_users()
    )

    tg_users = (
        get_users_from_telegram()
    )

    merged = sorted(
        list(
            dict.fromkeys(
                file_users
                +
                tg_users
            )
        )
    )

    save_users(
        merged
    )

    logger.info(
        f"👥 merged="
        f"{len(merged)}"
    )

    return merged


def remove_user(
    user_id,
    users
):

    try:

        if (
            user_id
            in users
        ):

            users.remove(
                user_id
            )

        save_users(
            users
        )

        logger.warning(
            f"🚫 removed "
            f"{user_id}"
        )

    except Exception as e:

        logger.error(
            f"remove fail: "
            f"{e}"
        )

# =====================================================
# FILE DISCOVERY
# =====================================================

def get_output_files():

    files = []

    for file_name in (
        DESIRED_FILES
    ):

        path = (
            OUTPUT_DIR
            / file_name
        )

        try:

            if (
                path.exists()
                and
                path.is_file()
                and
                path.stat()
                .st_size
                > 0
            ):

                files.append(
                    str(path)
                )

        except Exception:
            pass

    logger.info(
        f"📁 files="
        f"{len(files)}"
    )

    return files

# =====================================================
# SAFE SEND
# =====================================================

async def safe_send_message(
    client,
    user_id,
    text,
    retries=
    RETRY_COUNT
):

    for attempt in range(
        retries
    ):

        try:

            return await (
                client
                .send_message(
                    user_id,
                    text
                )
            )

        except (
            FloodWaitError
        ) as e:

            wait_time = (
                e.seconds
                + 2
            )

            logger.warning(
                f"⏳ wait "
                f"{wait_time}s"
            )

            await asyncio.sleep(
                wait_time
            )

        except (
            UserIsBlockedError,
            ChatWriteForbiddenError
        ):
            raise

        except Exception as e:

            logger.warning(
                f"msg retry "
                f"{attempt+1}"
                f"/"
                f"{retries} "
                f"{e}"
            )

            await asyncio.sleep(
                2
            )

    return None


async def safe_send_file(
    client,
    user_id,
    file_path,
    retries=
    RETRY_COUNT
):

    for attempt in range(
        retries
    ):

        try:

            return await (
                client
                .send_file(
                    user_id,
                    file_path,
                    caption=(
                        "📦 "
                        + os.path
                        .basename(
                            file_path
                        )
                    )
                )
            )

        except (
            FloodWaitError
        ) as e:

            wait_time = (
                e.seconds
                + 2
            )

            await asyncio.sleep(
                wait_time
            )

        except (
            UserIsBlockedError,
            ChatWriteForbiddenError
        ):
            raise

        except Exception as e:

            logger.warning(
                f"file retry "
                f"{attempt+1}"
                f"/"
                f"{retries} "
                f"{e}"
            )

            await asyncio.sleep(
                2
            )

    return None

# =====================================================
# HELPERS
# =====================================================

def build_intro_message():

    return (
        "🟢 Config "
        "Update Ready\n\n"

        "📦 Files:\n"
        "• configs.txt\n"
        "• country split\n"
        "• subscription links\n"
        "• project subscription\n\n"

        "🌍 Countries:\n"
        "IR / US / DE / "
        "TR / NL / FI "
        "/ SG / AE\n\n"

        "🚀 Updated"
    )


def build_help_message():

    return (
        "📘 Commands\n\n"
        "/start\n"
        "/help\n"
        "/ping\n"
        "/stats"
    )

# =====================================================
# PARALLEL SEND (B2)
# =====================================================

async def send_to_user(
    client,
    user_id,
    files,
    users
):

    try:

        await safe_send_message(
            client,
            user_id,
            build_intro_message()
        )

        await asyncio.sleep(
            0.7
        )

        sent = 0

        for file_path in (
            files
        ):

            result = await (
                safe_send_file(
                    client,
                    user_id,
                    file_path
                )
            )

            if result:
                sent += 1

            await asyncio.sleep(
                SEND_DELAY
            )

        logger.info(
            f"✅ "
            f"{user_id} "
            f"{sent}/"
            f"{len(files)}"
        )

        return (
            "success"
        )

    except (
        UserIsBlockedError,
        ChatWriteForbiddenError
    ):

        remove_user(
            user_id,
            users
        )

        return (
            "removed"
        )

    except Exception as e:

        logger.error(
            f"{user_id}: "
            f"{e}"
        )

        return (
            "failed"
        )


async def process_user_batch(
    client,
    batch,
    files,
    users
):

    tasks = [

        send_to_user(
            client,
            uid,
            files,
            users
        )

        for uid in batch
    ]

    return await (
        asyncio.gather(
            *tasks,
            return_exceptions=
            True
        )
    )# =====================================================
# MAIN
# =====================================================

async def main():

    logger.info(
        "🤖 bot started"
    )

    client = TelegramClient(
        "bot_session",
        API_ID,
        API_HASH
    )

    try:

        await client.start(
            bot_token=
            BOT_TOKEN
        )

        logger.info(
            "✅ connected"
        )

    except Exception as e:

        logger.exception(
            f"connect fail: "
            f"{e}"
        )

        return

    # =================================================
    # COMMANDS
    # =================================================

    @client.on(
        events.NewMessage(
            pattern=
            r"^/start$"
        )
    )
    async def start_handler(
        event
    ):

        uid = int(
            event.sender_id
        )

        users = (
            get_all_users()
        )

        if uid not in users:

            users.append(
                uid
            )

            save_users(
                users
            )

            logger.info(
                f"➕ "
                f"{uid}"
            )

        await safe_send_message(
            client,
            uid,
            (
                "👋 سلام\n\n"
                "ربات فعال شد.\n"
                "بعد از هر "
                "آپدیت فایل‌ها "
                "برای شما ارسال "
                "می‌شوند.\n\n"
                "دستورات:\n"
                "/help\n"
                "/stats\n"
                "/ping"
            )
        )

    @client.on(
        events.NewMessage(
            pattern=
            r"^/help$"
        )
    )
    async def help_handler(
        event
    ):

        await (
            safe_send_message(
                client,
                event.sender_id,
                build_help_message()
            )
        )

    @client.on(
        events.NewMessage(
            pattern=
            r"^/ping$"
        )
    )
    async def ping_handler(
        event
    ):

        await (
            safe_send_message(
                client,
                event.sender_id,
                (
                    "🏓 Pong\n"
                    "Bot Online ✅"
                )
            )
        )

    @client.on(
        events.NewMessage(
            pattern=
            r"^/stats$"
        )
    )
    async def stats_handler(
        event
    ):

        users = (
            get_all_users()
        )

        files = (
            get_output_files()
        )

        analytics = (
            load_analytics()
        )

        msg = (
            "📊 Bot Stats\n\n"
            f"👥 Users: "
            f"{len(users)}\n"
            f"📁 Files: "
            f"{len(files)}\n"
            f"✅ Success: "
            f"{analytics.get('success',0)}\n"
            f"❌ Failed: "
            f"{analytics.get('failed',0)}\n"
            f"🚫 Removed: "
            f"{analytics.get('removed',0)}\n"
            f"🕒 Last Run:\n"
            f"{analytics.get('last_run','-')}"
        )

        await (
            safe_send_message(
                client,
                event.sender_id,
                msg
            )
        )

    # =================================================
    # WAIT EVENTS REGISTER
    # =================================================

    await asyncio.sleep(
        2
    )

    # =================================================
    # USERS
    # =================================================

    users = (
        get_all_users()
    )

    if not users:

        logger.warning(
            "⚠️ no users"
        )

        await client.disconnect()
        return

    logger.info(
        f"👥 total="
        f"{len(users)}"
    )

    # =================================================
    # FILES
    # =================================================

    files = (
        get_output_files()
    )

    if not files:

        logger.warning(
            "⚠️ no files"
        )

        await client.disconnect()
        return

    logger.info(
        f"📁 total="
        f"{len(files)}"
    )

    # =================================================
    # BATCH SEND (8 USERS)
    # =================================================

    success_count = 0
    failed_count = 0
    removed_count = 0

    for i in range(
        0,
        len(users),
        PARALLEL_USERS
    ):

        batch = (
            users[
                i:
                i
                +
                PARALLEL_USERS
            ]
        )

        logger.info(
            f"🚀 batch "
            f"{batch}"
        )

        results = await (
            process_user_batch(
                client,
                batch,
                files,
                users
            )
        )

        for result in (
            results
        ):

            if (
                result
                ==
                "success"
            ):
                success_count += 1

            elif (
                result
                ==
                "removed"
            ):
                removed_count += 1

            else:
                failed_count += 1

        await asyncio.sleep(
            2
        )

    # =================================================
    # ANALYTICS SAVE
    # =================================================

    save_analytics(
        success=
        success_count,
        failed=
        failed_count,
        removed=
        removed_count
    )

    logger.info(
        "=================="
    )

    logger.info(
        f"✅ success="
        f"{success_count}"
    )

    logger.info(
        f"❌ failed="
        f"{failed_count}"
    )

    logger.info(
        f"🚫 removed="
        f"{removed_count}"
    )

    logger.info(
        "=================="
    )

    # =================================================
    # KEEP BOT ALIVE
    # =================================================

    logger.info(
        "⏳ commands..."
    )

    await asyncio.sleep(
        25
    )

    try:

        await (
            client
            .disconnect()
        )

    except Exception:
        pass

    logger.info(
        "🏁 finished"
    )

# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    try:

        logger.info(
            "🚀 process "
            "start"
        )

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.warning(
            "manual stop"
        )

    except RuntimeError as e:

        logger.exception(
            f"runtime "
            f"{e}"
        )

    except Exception as e:

        logger.exception(
            f"fatal "
            f"{e}"
        )

    finally:

        logger.info(
            "🧹 cleanup"
        )

        logger.info(
            "🏁 exit"
        )