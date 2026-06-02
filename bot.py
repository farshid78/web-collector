# ==========================================================
# BOT.PY (PART 1/3)
# Production Grade Telegram Sender Bot
# Foundation + Config + Managers
# ==========================================================

from __future__ import annotations

# ==========================================================
# IMPORTS
# ==========================================================

import os
import json
import time
import hashlib
import asyncio
import logging

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

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

BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
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

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN missing"
    )

# ==========================================================
# PATHS
# ==========================================================

ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .resolve()
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

USERS_FILE = (
    ROOT_DIR
    / "users.json"
)

ANALYTICS_FILE = (
    STATE_DIR
    / "analytics.json"
)
FILE_HASHES_FILE = (
    STATE_DIR
    / "file_hashes.json"
)

# ==========================================================
# CREATE DIRS
# ==========================================================

OUTPUT_DIR.mkdir(
    exist_ok=True
)

STATE_DIR.mkdir(
    exist_ok=True
)

LOGS_DIR.mkdir(
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
            / "bot.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(
    "SENDER_BOT"
)

# ==========================================================
# SETTINGS
# ==========================================================

PARALLEL_USERS = 8
RETRY_COUNT = 3
SEND_DELAY = 0.8

# فایل‌هایی که باید ارسال شوند
# bundle_info و project_subscription
# عمداً حذف شدند
DESIRED_FILES = [

    "configs.txt",

    "subscription_links.txt",

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

PROJECT_SUBSCRIPTION_LINK = (
    "https://raw.githubusercontent.com/"
    "farshid78/"
    "web-collector/"
    "main/output/configs.txt"
)

SUPPORTED_COUNTRIES = [
    "IR",
    "TR",
    "US",
    "DE",
    "NL",
    "FI",
    "SG",
    "AE"
]

# ==========================================================
# FILE HELPERS
# ==========================================================

def atomic_write(
    path: Path,
    data
):
    """
    نوشتن امن فایل
    برای جلوگیری از corruption
    """

    temp_path = (
        path.with_suffix(
            ".tmp"
        )
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_path,
        path
    )


# ==========================================================
# USER MANAGER
# ==========================================================

class UserManager:
    """
    مدیریت کاربران
    """

    def __init__(self):

        self.file_path = (
            USERS_FILE
        )

        self.lock = (
            asyncio.Lock()
        )

    async def load_users(
        self
    ) -> List[int]:

        async with self.lock:

            try:

                if not (
                    self.file_path
                    .exists()
                ):

                    with open(
                        self.file_path,
                        "w",
                        encoding="utf-8"
                    ) as f:

                        json.dump(
                            [],
                            f
                        )

                    return []

                with open(
                    self.file_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    data = (
                        json.load(
                            f
                        )
                    )

                users = []

                for uid in data:

                    try:

                        uid = int(uid)

                        if (
                            uid
                            not in users
                        ):
                            users.append(
                                uid
                            )

                    except Exception:
                        pass

                logger.info(
                    f"Users Loaded="
                    f"{len(users)}"
                )

                return sorted(
                    users
                )

            except Exception as e:

                logger.error(
                    f"Load Users "
                    f"Error: {e}"
                )

                return []

    async def save_users(
        self,
        users: List[int]
    ):

        async with self.lock:

            try:

                users = sorted(
                    list(
                        dict.fromkeys(
                            int(x)
                            for x in users
                        )
                    )
                )

                atomic_write(
                    self.file_path,
                    users
                )

            except Exception as e:

                logger.error(
                    f"Save Users "
                    f"Error: {e}"
                )

    async def add_user(
        self,
        user_id: int
    ):

        users = await (
            self.load_users()
        )

        if (
            user_id
            not in users
        ):

            users.append(
                user_id
            )

            await (
                self.save_users(
                    users
                )
            )

            logger.info(
                f"User Added "
                f"{user_id}"
            )

    async def remove_user(
        self,
        user_id: int
    ):

        users = await (
            self.load_users()
        )

        if (
            user_id
            in users
        ):

            users.remove(
                user_id
            )

            await (
                self.save_users(
                    users
                )
            )

            logger.warning(
                f"User Removed "
                f"{user_id}"
            )


# ==========================================================
# ANALYTICS MANAGER
# ==========================================================

class AnalyticsManager:
    """
    مدیریت آمار سیستم
    """

    def __init__(self):

        self.file_path = (
            ANALYTICS_FILE
        )

    def load(
        self
    ) -> Dict:

        try:

            if not (
                self.file_path
                .exists()
            ):
                return {}

            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(
                    f
                )

        except Exception:

            return {}

    def save(
        self,
        success: int = 0,
        failed: int = 0,
        removed: int = 0
    ):

        analytics = (
            self.load()
        )

        analytics[
            "last_run"
        ] = (
            datetime.utcnow()
            .strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
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

        atomic_write(
            self.file_path,
            analytics
        )


# ==========================================================
# OUTPUT FILES
# ==========================================================

def get_output_files() -> List[str]:
    """
    کشف فایل‌های خروجی معتبر
    """

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
                and path.is_file()
                and path.stat()
                .st_size > 30
            ):

                files.append(
                    str(path)
                )

        except Exception:
            pass

    logger.info(
        f"Output Files="
        f"{len(files)}"
    )

    return files


def get_changed_files(
    files: List[str]
) -> List[str]:
    """
    تشخیص فایل‌های تغییر‌یافته
    بر اساس hash
    """

    try:

        hashes = {}

        if FILE_HASHES_FILE.exists():

            with open(
                FILE_HASHES_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                hashes = json.load(f)

        changed_files = []
        new_hashes = {}

        for file_path in files:

            try:

                with open(
                    file_path,
                    "rb"
                ) as f:

                    file_hash = hashlib.sha256(
                        f.read()
                    ).hexdigest()

                new_hashes[file_path] = (
                    file_hash
                )

                if (
                    hashes.get(
                        file_path
                    )
                    != file_hash
                ):

                    changed_files.append(
                        file_path
                    )

            except Exception:
                pass

        atomic_write(
            FILE_HASHES_FILE,
            new_hashes
        )

        return changed_files

    except Exception as e:

        logger.error(
            f"Changed Files Error: {e}"
        )

        return files


# ==========================================================
# PROFESSIONAL UPDATE UI
# ==========================================================

def build_update_message():

    files = (
        get_output_files()
    )

    total_configs = 0

    try:

        configs_file = (
            OUTPUT_DIR
            / "configs.txt"
        )

        if configs_file.exists():

            with open(
                configs_file,
                "r",
                encoding="utf-8"
            ) as f:

                total_configs = len(
                    [
                        x for x
                        in f.read()
                        .splitlines()
                        if x.strip()
                    ]
                )

    except Exception:
        pass

    return f"""
╔════════════════════════════════════╗
    🤖 کانفیگ‌های جدید آماده ارسال
╚════════════════════════════════════╝

سلام 👋

بسته جدید کانفیگ‌ها آماده شد.

📦 تعداد کانفیگ‌ها:
{total_configs}

🌍 کشورها:
{' / '.join(SUPPORTED_COUNTRIES)}

📁 فایل‌های آماده:
{len(files)}

🔗 Subscription Link:
{PROJECT_SUBSCRIPTION_LINK}

🕒 زمان بروزرسانی:
{datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}

   ━━━━━━━━━━━━━━         ━━━━━━━━━━━━━━
    ✅ فایل‌ها در ادامه ارسال می‌شوند
    ━━━━━━━━━━━━━━        ━━━━━━━━━━━━━━
""".strip()
# ==========================================================
# BOT.PY (PART 2/3)
# Sender Pipeline + Commands + Safe Send
# ==========================================================

# ==========================================================
# SAFE SEND HELPERS
# ==========================================================

async def safe_send_message(
    client: TelegramClient,
    user_id: int,
    text: str,
    retries: int = RETRY_COUNT
):
    """
    ارسال امن پیام
    مدیریت FloodWait + Retry
    """

    for attempt in range(retries):

        try:

            result = await client.send_message(
                entity=user_id,
                message=text
            )

            return result

        except FloodWaitError as e:

            wait_time = e.seconds + 2

            logger.warning(
                f"FloodWait Message "
                f"{user_id} "
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
                f"Message Retry "
                f"{attempt+1}/"
                f"{retries} "
                f"{user_id}: {e}"
            )

            await asyncio.sleep(2)

    return None


async def safe_send_file(
    client: TelegramClient,
    user_id: int,
    file_path: str,
    retries: int = RETRY_COUNT
):
    """
    ارسال امن فایل
    """

    for attempt in range(retries):

        try:

            result = await client.send_file(
                entity=user_id,
                file=file_path
            )

            return result

        except FloodWaitError as e:

            wait_time = e.seconds + 2

            logger.warning(
                f"FloodWait File "
                f"{user_id} "
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
                f"File Retry "
                f"{attempt+1}/"
                f"{retries} "
                f"{user_id}: {e}"
            )

            await asyncio.sleep(2)

    return None


# ==========================================================
# PROFESSIONAL UI
# ==========================================================

def build_start_message():

    return """
╔════════════════════╗
🤖 ربات بروزرسانی کانفیگ
╚════════════════════╝

سلام 👋

ربات با موفقیت فعال شد.

از این لحظه بعد از هر بروزرسانی،
فایل‌های جدید به‌صورت خودکار
برای شما ارسال می‌شوند.

📦 امکانات:

• ارسال خودکار فایل‌ها
• تفکیک کانفیگ کشورها
• Subscription Links
• بروزرسانی منظم

📌 دستورات:

/help
/ping
/stats

━━━━━━━━━━━━━━
✅ سرویس فعال شد
━━━━━━━━━━━━━━
""".strip()


def build_help_message():

    return """
╔════════════════════╗
📘 راهنمای ربات
╚════════════════════╝

دستورات:

/start
فعال‌سازی ربات

/help
نمایش راهنما

/ping
بررسی وضعیت اتصال

/stats
نمایش آمار سیستم

━━━━━━━━━━━━━━
🤖 Auto Config Delivery
━━━━━━━━━━━━━━
""".strip()


def build_ping_message():

    return f"""
🏓 Pong

✅ وضعیت:
آنلاین

⚡ اتصال:
فعال

🕒 زمان:
{datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
""".strip()


# ==========================================================
# SEND TO USER
# ==========================================================

async def send_to_user(
    client: TelegramClient,
    user_id: int,
    files: List[str],
    user_manager: UserManager
):
    """
    ارسال حرفه‌ای فایل‌ها برای هر کاربر
    """

    try:

        # پیام بروزرسانی
        await safe_send_message(
            client,
            user_id,
            build_update_message()
        )

        await asyncio.sleep(1)

        sent_count = 0

        for file_path in files:

            result = await safe_send_file(
                client,
                user_id,
                file_path
            )

            if result:
                sent_count += 1

            await asyncio.sleep(
                SEND_DELAY
            )

        logger.info(
            f"Send Success "
            f"{user_id} "
            f"{sent_count}/"
            f"{len(files)}"
        )

        return "success"

    except (
        UserIsBlockedError,
        ChatWriteForbiddenError
    ):

        await user_manager.remove_user(
            user_id
        )

        logger.warning(
            f"Removed User "
            f"{user_id}"
        )

        return "removed"

    except Exception as e:

        logger.error(
            f"Send Failed "
            f"{user_id}: {e}"
        )

        return "failed"


# ==========================================================
# PARALLEL PIPELINE
# ==========================================================

async def process_batch(
    client: TelegramClient,
    users: List[int],
    files: List[str],
    user_manager: UserManager
):
    """
    ارسال موازی کنترل‌شده
    """

    semaphore = asyncio.Semaphore(
        PARALLEL_USERS
    )

    async def worker(uid):

        async with semaphore:

            return await send_to_user(
                client=client,
                user_id=uid,
                files=files,
                user_manager=user_manager
            )

    tasks = [
        worker(uid)
        for uid in users
    ]

    return await asyncio.gather(
        *tasks,
        return_exceptions=True
    )


# ==========================================================
# COMMAND HANDLERS
# ==========================================================

async def register_handlers(
    client: TelegramClient,
    user_manager: UserManager
):
    """
    ثبت commandها
    """

    @client.on(
        events.NewMessage(
            pattern=r"^/start$"
        )
    )
    async def start_handler(event):

        user_id = int(
            event.sender_id
        )

        await user_manager.add_user(
            user_id
        )

        await safe_send_message(
            client,
            user_id,
            build_start_message()
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
            build_ping_message()
        )

    @client.on(
        events.NewMessage(
            pattern=r"^/stats$"
        )
    )
    async def stats_handler(event):

            analytics = (
                AnalyticsManager()
                .load()
            )
    
            users = await (
                user_manager
                .load_users()
            )
    
            files = get_changed_files(
                get_output_files()
            )
    
            text = f"""
    👥 کاربران:
    {len(users)}
    
    📁 فایل‌ها:
    {len(files)}
    
    ✅ ارسال موفق:
    {analytics.get("success",0)}
    
    ❌ خطا:
    {analytics.get("failed",0)}
    
    🚫 حذف‌شده:
    {analytics.get("removed",0)}
    
    🕒 آخرین اجرا:
    {analytics.get("last_run","-")}
    
    ━━━━━━━━━━━━━━
    🤖 Production Bot
    ━━━━━━━━━━━━━━
    """.strip()
    
            await safe_send_message(
                client,
                event.sender_id,
                text
            )

    logger.info(
        "Handlers Registered"
    )
    # ==========================================================
# BOT.PY (PART 3/3)
# Main Lifecycle + Auto Sender + Graceful Shutdown
# ==========================================================

# ==========================================================
# RUN SENDER PIPELINE
# ==========================================================

async def run_sender_pipeline(
    client: TelegramClient,
    user_manager: UserManager
):
    """
    اجرای pipeline ارسال فایل‌ها
    """

    logger.info(
        "Starting Sender Pipeline"
    )

    users = await (
        user_manager
        .load_users()
    )

    if not users:

        logger.warning(
            "No users found"
        )
        return

    files = get_output_files()
    files = get_changed_files(files)

    if not files:

        logger.info(
            "ℹ️ no changed files"
        )
        return

    success_count = 0
    failed_count = 0
    removed_count = 0

    try:

        results = await process_batch(
            client=client,
            users=users,
            files=files,
            user_manager=user_manager
        )

        for result in results:

            if result == "success":

                success_count += 1

            elif result == "removed":

                removed_count += 1

            else:

                failed_count += 1

    except Exception as e:

        logger.exception(
            f"Pipeline Error: {e}"
        )

    # ======================================
    # SAVE ANALYTICS
    # ======================================

    AnalyticsManager().save(
        success=success_count,
        failed=failed_count,
        removed=removed_count
    )

    logger.info(
        "===================="
    )

    logger.info(
        f"Success={success_count}"
    )

    logger.info(
        f"Failed={failed_count}"
    )

    logger.info(
        f"Removed={removed_count}"
    )

    logger.info(
        "===================="
    )


# ==========================================================
# CLIENT FACTORY
# ==========================================================

async def create_client():
    """
    ساخت Telegram Client
    """

    logger.info(
        "Connecting Telegram..."
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
            "Telegram Connected"
        )

        return client

    except Exception as e:

        logger.exception(
            f"Client Error: {e}"
        )

        try:

            await client.disconnect()

        except Exception:
            pass

        raise


# ==========================================================
# MAIN
# ==========================================================

async def main():
    """
    Main Application
    """

    logger.info(
        "🚀 Bot Starting..."
    )

    start_time = time.time()

    client = None

    try:

        # ==================================
        # INIT MANAGERS
        # ==================================

        user_manager = (
            UserManager()
        )

        # ==================================
        # CONNECT CLIENT
        # ==================================

        client = await (
            create_client()
        )

        # ==================================
        # REGISTER COMMANDS
        # ==================================

        await register_handlers(
            client,
            user_manager
        )

        logger.info(
            "Commands Registered"
        )

        # ==================================
        # WAIT FOR TELEGRAM READY
        # ==================================

        await asyncio.sleep(2)

        # ==================================
        # AUTO SEND FILES
        # ==================================

        await run_sender_pipeline(
            client,
            user_manager
        )

        # ==================================
        # KEEP BOT ONLINE
        # برای دریافت commandها
        # ==================================

        logger.info(
            "Bot Online..."
        )

        await asyncio.sleep(540)

        elapsed = round(
            time.time()
            - start_time,
            2
        )

        logger.info(
            f"Finished in "
            f"{elapsed}s"
        )

    except KeyboardInterrupt:

        logger.warning(
            "Interrupted"
        )

    except Exception as e:

        logger.exception(
            f"Fatal Error: {e}"
        )

    finally:

        logger.info(
            "Graceful Shutdown..."
        )

        try:

            if client:

                await client.disconnect()

        except Exception as e:

            logger.warning(
                f"Disconnect Error: "
                f"{e}"
            )

        logger.info(
            "🏁 Exit"
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
            "Stopped Manually"
        )

    except RuntimeError as e:

        logger.exception(
            f"Runtime Error: {e}"
        )

    except Exception as e:

        logger.exception(
            f"Crash: {e}"
        )

    finally:

        logger.info(
            "Cleanup Done"
        )
    