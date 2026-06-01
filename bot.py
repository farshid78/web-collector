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

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError(
        "Missing env vars: API_ID / API_HASH / TELEGRAM_BOT_TOKEN"
    )

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

# فایل‌هایی که باید ارسال شوند
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
    Save unique users
    """
    users = list(dict.fromkeys(users))

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

        if isinstance(data, list):
            return list(dict.fromkeys(data))

        return []

    except Exception as e:
        logger.error(f"Load users failed: {e}")
        return []


def remove_user(user_id, users):
    """
    Remove blocked/dead user
    """
    try:
        users.remove(user_id)
        save_users(users)

        logger.warning(
            f"Removed blocked user: {user_id}"
        )

    except Exception as e:
        logger.error(
            f"Remove user error: {e}"
        )

# =====================================================
# TELEGRAM UPDATE FETCH
# =====================================================

def get_users_from_telegram():
    """
    Fetch new users from getUpdates
    """
    try:
        url = (
            f"https://api.telegram.org"
            f"/bot{BOT_TOKEN}"
            f"/getUpdates"
            f"?allowed_updates=message"
        )

        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT
        )

        if r.status_code != 200:
            return []

        result = r.json().get(
            "result",
            []
        )

        users = []

        for update in result:
            try:
                uid = update["message"]["from"]["id"]
                users.append(uid)
            except Exception:
                continue

        return list(dict.fromkeys(users))

    except Exception as e:
        logger.error(
            f"getUpdates failed: {e}"
        )
        return []

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
            if path.exists() and path.stat().st_size > 0:
                files.append(str(path))
        except Exception:
            continue

    logger.info(f"Files to send: {files}")

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
    Retry send message
    """
    for attempt in range(retries):

        try:
            return await client.send_message(
                user_id,
                text
            )

        except FloodWaitError as e:
            wait_time = e.seconds + 2

            logger.warning(
                f"FloodWait {wait_time}s"
            )

            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(
                f"send_message retry "
                f"{attempt+1}/{retries}: {e}"
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
    Retry send file
    """
    for attempt in range(retries):

        try:
            return await client.send_file(
                user_id,
                file_path
            )

        except FloodWaitError as e:
            wait_time = e.seconds + 2

            logger.warning(
                f"FloodWait {wait_time}s"
            )

            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(
                f"send_file retry "
                f"{attempt+1}/{retries}: {e}"
            )

            await asyncio.sleep(2)

    return None
    # =====================================================
# MAIN
# =====================================================

async def main():
    logger.info("🤖 BOT STARTED")

    users = load_users()

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

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):

        uid = event.sender_id

        if uid not in users:
            users.append(uid)
            save_users(users)

            logger.info(
                f"➕ New user added: {uid}"
            )

        msg = (
            "👋 سلام\n\n"
            "ربات فعال است.\n"
            "هر بار آپدیت جدید انجام شود "
            "فایل‌های کانفیگ برای شما "
            "ارسال می‌شوند.\n\n"
            "دستورات:\n"
            "/help\n"
            "/stats\n"
            "/ping"
        )

        await safe_send_message(
            client,
            uid,
            msg
        )

    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def help_handler(event):

        msg = (
            "📘 راهنما\n\n"
            "/start → فعال‌سازی ربات\n"
            "/stats → تعداد کاربران\n"
            "/ping → تست آنلاین بودن ربات\n\n"
            "فایل‌ها بعد از هر "
            "آپدیت اسکریپر ارسال می‌شوند."
        )

        await safe_send_message(
            client,
            event.sender_id,
            msg
        )

    @client.on(events.NewMessage(pattern=r"^/stats$"))
    async def stats_handler(event):

        files = get_config_files()

        msg = (
            "📊 Bot Stats\n\n"
            f"👥 Users: {len(users)}\n"
            f"📁 Files: {len(files)}\n"
        )

        await safe_send_message(
            client,
            event.sender_id,
            msg
        )

    @client.on(events.NewMessage(pattern=r"^/ping$"))
    async def ping_handler(event):

        await safe_send_message(
            client,
            event.sender_id,
            "🏓 Pong\nBot Online ✅"
        )

    # =================================================
    # UPDATE USERS
    # =================================================

    logger.info(
        "🔍 Checking new users..."
    )

    try:
        new_users = get_users_from_telegram()

        for uid in new_users:

            if uid not in users:
                users.append(uid)

                logger.info(
                    f"➕ Added user: {uid}"
                )

        save_users(users)

    except Exception as e:
        logger.error(
            f"Update users failed: {e}"
        )

    # =================================================
    # PREPARE FILES
    # =================================================

    config_files = get_config_files()

    if not config_files:
        logger.warning(
            "No config files found"
        )

        await asyncio.sleep(10)

        await client.disconnect()
        return

    logger.info(
        f"📁 Total files: "
        f"{len(config_files)}"
    )

    logger.info(
        f"👥 Users: {len(users)}"
    )
        # =================================================
    # SEND FILES TO USERS
    # =================================================

    for index, user_id in enumerate(users.copy(), start=1):

        logger.info(
            f"[{index}/{len(users)}] "
            f"Sending to {user_id}"
        )

        try:
            # -----------------------------------------
            # Intro Message
            # -----------------------------------------

            intro_message = (
                "🟢 آپدیت جدید کانفیگ‌ها آماده شد\n\n"
                "📦 فایل‌ها بر اساس کشور "
                "دسته‌بندی شده‌اند.\n\n"
                "کشورها:\n"
                "🇮🇷 IR\n"
                "🇺🇸 US\n"
                "🇩🇪 DE\n"
                "🇳🇱 NL\n"
                "🇹🇷 TR\n"
                "🇫🇮 FI\n"
                "🇸🇬 SG\n"
                "🌍 Others"
            )

            await safe_send_message(
                client,
                user_id,
                intro_message
            )

            # -----------------------------------------
            # Send Files
            # -----------------------------------------

            for file_path in config_files:

                file_name = os.path.basename(
                    file_path
                )

                logger.info(
                    f" ↳ Sending "
                    f"{file_name}"
                )

                result = await safe_send_file(
                    client,
                    user_id,
                    file_path
                )

                if result is None:
                    logger.warning(
                        f"Failed file: "
                        f"{file_name}"
                    )

                await asyncio.sleep(
                    SEND_DELAY
                )

            logger.info(
                f"✅ Done for {user_id}"
            )

        # ---------------------------------------------
        # Flood Wait
        # ---------------------------------------------

        except FloodWaitError as e:

            wait_time = e.seconds + 5

            logger.warning(
                f"FloodWait "
                f"{wait_time}s"
            )

            await asyncio.sleep(
                wait_time
            )

        # ---------------------------------------------
        # Blocked User
        # ---------------------------------------------

        except (
            UserIsBlockedError,
            ChatWriteForbiddenError
        ):

            logger.warning(
                f"🚫 User blocked bot: "
                f"{user_id}"
            )

            remove_user(
                user_id,
                users
            )

        # ---------------------------------------------
        # Unknown Error
        # ---------------------------------------------

        except Exception as e:

            logger.exception(
                f"Send failed "
                f"for {user_id}: {e}"
            )

            await asyncio.sleep(2)

    # =================================================
    # WAIT EVENTS
    # =================================================

    logger.info(
        "⏳ Waiting for commands..."
    )

    await asyncio.sleep(25)

    # =================================================
    # CLEAN SHUTDOWN
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
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.warning(
            "Interrupted manually"
        )

    except Exception as e:
        logger.exception(
            f"Fatal bot error: {e}"
        )
