import os
import json
import asyncio
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    UserIsBlockedError,
    ChatWriteForbiddenError,
)

# =====================================================
# ENV
# =====================================================

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not API_ID:
    raise RuntimeError("API_ID missing")

if not API_HASH:
    raise RuntimeError("API_HASH missing")

if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN missing")

# =====================================================
# PATHS
# =====================================================

ROOT_DIR = Path(__file__).resolve().parent

USERS_FILE = ROOT_DIR / "users.json"
LOGS_DIR = ROOT_DIR / "logs"

LOGS_DIR.mkdir(exist_ok=True)

# =====================================================
# LOGGING
# =====================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOGS_DIR / "bot.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("BOT")

# =====================================================
# SETTINGS
# =====================================================

SEND_DELAY = 1.2
RETRY_COUNT = 3
REQUEST_TIMEOUT = 10

DESIRED_FILES = [
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
# USER MANAGEMENT
# =====================================================

def save_users(users):
    """
    Save unique users safely
    """
    try:
        users = sorted(
            list(
                dict.fromkeys(
                    int(u)
                    for u in users
                    if str(u).isdigit()
                )
            )
        )

        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(
            f"💾 Saved users: {len(users)}"
        )

    except Exception as e:
        logger.error(
            f"save_users failed: {e}"
        )


def load_users():
    """
    Load users safely
    """
    if not USERS_FILE.exists():
        save_users([])
        return []

    try:
        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        users = []

        for uid in data:
            try:
                uid = int(uid)

                if uid not in users:
                    users.append(uid)

            except Exception:
                continue

        logger.info(
            f"📥 Loaded users: {len(users)}"
        )

        return users

    except Exception as e:
        logger.error(
            f"load_users failed: {e}"
        )
        return []


def remove_user(user_id, users):
    """
    Remove blocked/dead user
    """
    try:
        if user_id in users:
            users.remove(user_id)

        save_users(users)

        logger.warning(
            f"🚫 Removed user: {user_id}"
        )

    except Exception as e:
        logger.error(
            f"remove_user failed: {e}"
        )

# =====================================================
# TELEGRAM USER FETCH
# =====================================================

def get_users_from_telegram():
    """
    Fetch users from Telegram getUpdates
    """

    logger.info(
        "🔍 Fetching users from Telegram..."
    )

    users = []

    try:
        url = (
            f"https://api.telegram.org"
            f"/bot{BOT_TOKEN}"
            f"/getUpdates"
        )

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            logger.warning(
                f"getUpdates bad status: "
                f"{response.status_code}"
            )
            return []

        data = response.json()

        for update in data.get(
            "result",
            []
        ):

            try:
                message = update.get(
                    "message",
                    {}
                )

                user = message.get(
                    "from",
                    {}
                )

                uid = user.get("id")

                if uid:
                    users.append(int(uid))

            except Exception:
                continue

        users = list(
            dict.fromkeys(users)
        )

        logger.info(
            f"📥 Telegram users: "
            f"{len(users)}"
        )

        return users

    except Exception as e:
        logger.error(
            f"getUpdates failed: {e}"
        )
        return []

# =====================================================
# MERGE USER SOURCES
# =====================================================

def get_all_users():
    """
    Merge:
    users.json
    +
    Telegram getUpdates
    """

    file_users = load_users()

    telegram_users = (
        get_users_from_telegram()
    )

    merged = sorted(
        list(
            dict.fromkeys(
                file_users +
                telegram_users
            )
        )
    )

    save_users(merged)

    logger.info(
        f"👥 Final merged users: "
        f"{len(merged)}"
    )

    return merged
    # =====================================================
# FILE DISCOVERY
# =====================================================

def get_config_files():
    """
    Return valid config files only
    """

    files = []

    for file_name in DESIRED_FILES:

        path = ROOT_DIR / file_name

        try:
            if (
                path.exists()
                and path.is_file()
                and path.stat().st_size > 0
            ):
                files.append(str(path))

        except Exception as e:
            logger.warning(
                f"file check failed "
                f"{file_name}: {e}"
            )

    logger.info(
        f"📁 Files discovered: "
        f"{len(files)}"
    )

    for f in files:
        logger.info(
            f" ↳ {os.path.basename(f)}"
        )

    return files


# =====================================================
# RETRY HELPERS
# =====================================================

async def safe_send_message(
    client,
    user_id,
    text,
    retries=RETRY_COUNT
):
    """
    Safe send message with retry
    """

    for attempt in range(
        retries
    ):

        try:

            return await client.send_message(
                user_id,
                text
            )

        except FloodWaitError as e:

            wait_time = (
                e.seconds + 2
            )

            logger.warning(
                f"⏳ FloodWait "
                f"{wait_time}s "
                f"user={user_id}"
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
                f"send_message "
                f"retry "
                f"{attempt+1}/"
                f"{retries} "
                f"user={user_id} "
                f"error={e}"
            )

            await asyncio.sleep(2)

    return None


async def safe_send_file(
    client,
    user_id,
    file_path,
    retries=RETRY_COUNT
):
    """
    Safe send file with retry
    """

    for attempt in range(
        retries
    ):

        try:

            return await client.send_file(
                user_id,
                file_path,
                caption=(
                    "📦 Config Update\n"
                    f"{os.path.basename(file_path)}"
                )
            )

        except FloodWaitError as e:

            wait_time = (
                e.seconds + 2
            )

            logger.warning(
                f"⏳ FloodWait "
                f"{wait_time}s "
                f"user={user_id}"
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
                f"send_file retry "
                f"{attempt+1}/"
                f"{retries} "
                f"user={user_id} "
                f"file="
                f"{os.path.basename(file_path)} "
                f"error={e}"
            )

            await asyncio.sleep(2)

    return None


# =====================================================
# BOT COMMAND HELPERS
# =====================================================

def build_help_message():

    return (
        "📘 راهنمای ربات\n\n"
        "/start → فعال‌سازی ربات\n"
        "/help → راهنما\n"
        "/stats → آمار ربات\n"
        "/ping → تست آنلاین بودن\n\n"
        "بعد از هر آپدیت، "
        "فایل‌های کانفیگ "
        "برای شما ارسال می‌شوند."
    )


def build_intro_message():

    return (
        "🟢 آپدیت جدید کانفیگ‌ها آماده شد\n\n"
        "📦 فایل‌ها بر اساس کشور "
        "دسته‌بندی شده‌اند.\n\n"
        "🇮🇷 IR\n"
        "🇺🇸 US\n"
        "🇩🇪 DE\n"
        "🇳🇱 NL\n"
        "🇹🇷 TR\n"
        "🇫🇮 FI\n"
        "🇸🇬 SG\n"
        "🇦🇪 AE\n"
        "🌍 Others"
    )
    # =====================================================
# MAIN
# =====================================================

async def main():

    logger.info(
        "🤖 BOT STARTED"
    )

    client = TelegramClient(
        "bot_session",
        API_ID,
        API_HASH
    )

    try:

        await client.start(
            bot_token=BOT_TOKEN
        )

        logger.info(
            "✅ Bot connected"
        )

    except Exception as e:

        logger.exception(
            f"Bot connection failed: {e}"
        )
        return

    # =================================================
    # COMMANDS
    # =================================================

    @client.on(
        events.NewMessage(
            pattern=r"^/start$"
        )
    )
    async def start_handler(event):

        uid = int(event.sender_id)

        users = get_all_users()

        if uid not in users:

            users.append(uid)
            save_users(users)

            logger.info(
                f"➕ New user: {uid}"
            )

        message = (
            "👋 سلام\n\n"
            "ربات فعال شد.\n"
            "بعد از هر آپدیت "
            "کانفیگ‌ها برای شما "
            "ارسال می‌شود.\n\n"
            "دستورات:\n"
            "/help\n"
            "/stats\n"
            "/ping"
        )

        await safe_send_message(
            client,
            uid,
            message
        )

    @client.on(
        events.NewMessage(
            pattern=r"^/help$"
        )
    )
    async def help_handler(event):

        await safe_send_message(
            client,
            event.sender_id,
            build_help_message()
        )

    @client.on(
        events.NewMessage(
            pattern=r"^/ping$"
        )
    )
    async def ping_handler(event):

        await safe_send_message(
            client,
            event.sender_id,
            "🏓 Pong\nBot Online ✅"
        )

    @client.on(
        events.NewMessage(
            pattern=r"^/stats$"
        )
    )
    async def stats_handler(event):

        users = get_all_users()
        files = get_config_files()

        message = (
            "📊 Bot Stats\n\n"
            f"👥 Users: {len(users)}\n"
            f"📁 Files: {len(files)}\n"
        )

        await safe_send_message(
            client,
            event.sender_id,
            message
        )

    # =================================================
    # WAIT SMALL TIME FOR EVENTS
    # =================================================

    await asyncio.sleep(2)

    # =================================================
    # USERS
    # =================================================

    users = get_all_users()

    if not users:

        logger.warning(
            "⚠️ No users found"
        )

        await asyncio.sleep(5)

        await client.disconnect()
        return

    logger.info(
        f"👥 Total users: "
        f"{len(users)}"
    )

    # =================================================
    # FILES
    # =================================================

    config_files = (
        get_config_files()
    )

    if not config_files:

        logger.warning(
            "⚠️ No config files found"
        )

        await asyncio.sleep(5)

        await client.disconnect()
        return

    logger.info(
        f"📁 Files: "
        f"{len(config_files)}"
    )

    # =================================================
    # SEND TO ALL USERS
    # =================================================

    success_count = 0
    failed_count = 0
    removed_count = 0

    for index, user_id in enumerate(
        users.copy(),
        start=1
    ):

        logger.info(
            f"[{index}/"
            f"{len(users)}] "
            f"Sending to "
            f"{user_id}"
        )

        try:

            # -----------------------------
            # Intro message
            # -----------------------------

            await safe_send_message(
                client,
                user_id,
                build_intro_message()
            )

            await asyncio.sleep(
                1
            )

            # -----------------------------
            # Files
            # -----------------------------

            sent_files = 0

            for file_path in (
                config_files
            ):

                logger.info(
                    f" ↳ "
                    f"{os.path.basename(file_path)}"
                )

                result = (
                    await safe_send_file(
                        client,
                        user_id,
                        file_path
                    )
                )

                if result:

                    sent_files += 1

                await asyncio.sleep(
                    SEND_DELAY
                )

            logger.info(
                f"✅ Sent "
                f"{sent_files}/"
                f"{len(config_files)} "
                f"files to "
                f"{user_id}"
            )

            success_count += 1

        # --------------------------------
        # FloodWait
        # --------------------------------

        except FloodWaitError as e:

            wait_time = (
                e.seconds + 5
            )

            logger.warning(
                f"⏳ FloodWait "
                f"{wait_time}s"
            )

            await asyncio.sleep(
                wait_time
            )

            failed_count += 1

        # --------------------------------
        # Blocked User
        # --------------------------------

        except (
            UserIsBlockedError,
            ChatWriteForbiddenError
        ):

            logger.warning(
                f"🚫 Blocked: "
                f"{user_id}"
            )

            remove_user(
                user_id,
                users
            )

            removed_count += 1

        # --------------------------------
        # Unknown error
        # --------------------------------

        except Exception as e:

            logger.exception(
                f"❌ Failed for "
                f"{user_id}: {e}"
            )

            failed_count += 1

            await asyncio.sleep(2)

    # =================================================
    # SUMMARY
    # =================================================

    logger.info(
        "================================"
    )

    logger.info(
        f"✅ Success: "
        f"{success_count}"
    )

    logger.info(
        f"❌ Failed: "
        f"{failed_count}"
    )

    logger.info(
        f"🚫 Removed: "
        f"{removed_count}"
    )

    logger.info(
        "================================"
    )

    # =================================================
    # KEEP BOT ALIVE FOR COMMANDS
    # =================================================

    logger.info(
        "⏳ Waiting commands..."
    )

    await asyncio.sleep(25)

    # =================================================
    # SHUTDOWN
    # =================================================

    try:
        await client.disconnect()

    except Exception:
        pass

    logger.info(
        "🏁 BOT FINISHED"
    )
    # =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    try:

        logger.info(
            "🚀 Starting bot process..."
        )

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        logger.warning(
            "⛔ Interrupted manually"
        )

    except RuntimeError as e:

        logger.exception(
            f"Runtime error: {e}"
        )

    except Exception as e:

        logger.exception(
            f"Fatal bot error: {e}"
        )

    finally:

        logger.info(
            "🧹 Cleanup finished"
        )

        logger.info(
            "🏁 Process exited"
        )
