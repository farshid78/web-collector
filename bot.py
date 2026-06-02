# ==========================================================
# BOT.PY (PART 1/3)
# Production Grade Telegram Sender Bot
# Foundation + Config + Managers
# ==========================================================

from __future__ import annotations

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

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, UserIsBlockedError, ChatWriteForbiddenError

# ==========================================================
# ENV
# ==========================================================

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not API_ID:
    raise RuntimeError("API_ID missing")

if not API_HASH:
    raise RuntimeError("API_HASH missing")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

# ==========================================================
# PATHS
# ==========================================================

ROOT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = ROOT_DIR / "output"
STATE_DIR = ROOT_DIR / "state"
LOGS_DIR = ROOT_DIR / "logs"

USERS_FILE = ROOT_DIR / "users.json"
ANALYTICS_FILE = STATE_DIR / "analytics.json"
FILE_HASHES_FILE = STATE_DIR / "file_hashes.json"

OUTPUT_DIR.mkdir(exist_ok=True)
STATE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SENDER_BOT")

# ==========================================================
# SETTINGS
# ==========================================================

PARALLEL_USERS = 8
RETRY_COUNT = 3
SEND_DELAY = 0.8

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

SUPPORTED_COUNTRIES = ["IR", "TR", "US", "DE", "NL", "FI", "SG", "AE"]

PROJECT_SUBSCRIPTION_LINK = (
    "https://raw.githubusercontent.com/"
    "farshid78/"
    "web-collector/"
    "main/output/configs.txt"
)

# ==========================================================
# FILE HELPERS
# ==========================================================

def atomic_write(path: Path, data):
    tmp = path.with_suffix(".tmp")

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.replace(tmp, path)

# ==========================================================
# DELTA SYSTEM (NEW)
# ==========================================================

def load_file_hashes():
    try:
        if not FILE_HASHES_FILE.exists():
            return {}

        with open(FILE_HASHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {}


def save_file_hashes(data):
    try:
        atomic_write(FILE_HASHES_FILE, data)
    except Exception as e:
        logger.warning(f"hash save fail {e}")


def get_file_hash(file_path: str):
    try:
        md5 = hashlib.md5()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                md5.update(chunk)

        return md5.hexdigest()

    except Exception:
        return None


def get_changed_files(files: List[str]) -> List[str]:
    previous = load_file_hashes()
    current = {}
    changed = []

    for path in files:

        name = os.path.basename(path)
        h = get_file_hash(path)

        if not h:
            continue

        current[name] = h

        if previous.get(name) != h:
            changed.append(path)

    save_file_hashes(current)

    logger.info(f"📦 changed={len(changed)}")

    return changed

# ==========================================================
# OUTPUT FILES (FIXED - SINGLE VERSION ONLY)
# ==========================================================

def get_output_files() -> List[str]:
    files = []

    for file_name in DESIRED_FILES:
        path = OUTPUT_DIR / file_name

        try:
            if path.exists() and path.is_file() and path.stat().st_size > 0:
                files.append(str(path))
        except Exception:
            pass

    logger.info(f"Output Files={len(files)}")
    return files

# ==========================================================
# ANALYTICS MANAGER
# ==========================================================

class AnalyticsManager:

    def __init__(self):
        self.file_path = ANALYTICS_FILE

    def load(self) -> Dict:
        try:
            if not self.file_path.exists():
                return {}
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, success=0, failed=0, removed=0):
        data = self.load()

        data["last_run"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        data["success"] = data.get("success", 0) + success
        data["failed"] = data.get("failed", 0) + failed
        data["removed"] = data.get("removed", 0) + removed

        atomic_write(self.file_path, data)

# ==========================================================
# SAFE SEND HELPERS
# ==========================================================

async def safe_send_message(
    client: TelegramClient,
    user_id: int,
    text: str,
    retries: int = RETRY_COUNT
):

    for attempt in range(retries):

        try:
            return await client.send_message(
                entity=user_id,
                message=text
            )

        except FloodWaitError as e:
            wait_time = e.seconds + 2
            logger.warning(f"FloodWait msg {user_id} {wait_time}s")
            await asyncio.sleep(wait_time)

        except (UserIsBlockedError, ChatWriteForbiddenError):
            raise

        except Exception as e:
            logger.warning(f"msg retry {attempt+1}/{retries}: {e}")
            await asyncio.sleep(2)

    return None


async def safe_send_file(
    client: TelegramClient,
    user_id: int,
    file_path: str,
    retries: int = RETRY_COUNT
):

    for attempt in range(retries):

        try:
            return await client.send_file(
                entity=user_id,
                file=file_path
            )

        except FloodWaitError as e:
            wait_time = e.seconds + 2
            logger.warning(f"FloodWait file {user_id} {wait_time}s")
            await asyncio.sleep(wait_time)

        except (UserIsBlockedError, ChatWriteForbiddenError):
            raise

        except Exception as e:
            logger.warning(f"file retry {attempt+1}/{retries}: {e}")
            await asyncio.sleep(2)

    return None


# ==========================================================
# UI MESSAGES
# ==========================================================

def build_start_message():

    return """
╔════════════════════╗
🤖 ربات بروزرسانی کانفیگ
╚════════════════════╝

سلام 👋

ربات فعال شد.

📦 ارسال خودکار فایل‌ها
🌍 تفکیک کشورها
🔗 Subscription لینک‌ها

دستورات:
/help /ping /stats
""".strip()


def build_help_message():

    return """
╔════════════════════╗
📘 راهنما
╚════════════════════╝

/start شروع
/help راهنما
/ping وضعیت
/stats آمار
""".strip()


def build_ping_message():

    return f"""
🏓 Pong

✅ آنلاین
⚡ فعال

🕒 {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
""".strip()


def build_update_message():

    files = get_output_files()

    total_configs = 0

    try:
        cfg = OUTPUT_DIR / "configs.txt"

        if cfg.exists():
            total_configs = len(
                [
                    x for x in cfg.read_text(encoding="utf-8").splitlines()
                    if x.strip()
                ]
            )
    except Exception:
        pass

    return f"""
🚀 بروزرسانی کانفیگ

📦 کانفیگ‌ها: {total_configs}
🌍 کشورها: {' / '.join(SUPPORTED_COUNTRIES)}
📁 فایل‌ها: {len(files)}

🔗 {PROJECT_SUBSCRIPTION_LINK}

🕒 {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
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

    try:

        await safe_send_message(
            client,
            user_id,
            build_update_message()
        )

        await asyncio.sleep(1)

        sent = 0

        for file_path in files:

            result = await safe_send_file(
                client,
                user_id,
                file_path
            )

            if result:
                sent += 1

            await asyncio.sleep(SEND_DELAY)

        logger.info(f"Send OK {user_id} {sent}/{len(files)}")

        return "success"

    except (UserIsBlockedError, ChatWriteForbiddenError):

        await user_manager.remove_user(user_id)
        logger.warning(f"User removed {user_id}")

        return "removed"

    except Exception as e:

        logger.error(f"Send error {user_id}: {e}")
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

    semaphore = asyncio.Semaphore(PARALLEL_USERS)

    async def worker(uid):

        async with semaphore:
            return await send_to_user(
                client,
                uid,
                files,
                user_manager
            )

    tasks = [worker(u) for u in users]

    return await asyncio.gather(*tasks, return_exceptions=True)


# ==========================================================
# COMMAND HANDLERS
# ==========================================================

async def register_handlers(client: TelegramClient, user_manager: UserManager):

    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start(event):

        uid = int(event.sender_id)

        await user_manager.add_user(uid)

        await safe_send_message(client, uid, build_start_message())


    @client.on(events.NewMessage(pattern=r"^/help$"))
    async def help(event):

        await safe_send_message(client, event.sender_id, build_help_message())


    @client.on(events.NewMessage(pattern=r"^/ping$"))
    async def ping(event):

        await safe_send_message(client, event.sender_id, build_ping_message())


    @client.on(events.NewMessage(pattern=r"^/stats$"))
    async def stats(event):

        analytics = AnalyticsManager().load()
        users = await user_manager.load_users()
        files = get_output_files()

        msg = f"""
📊 Stats

👥 Users: {len(users)}
📁 Files: {len(files)}

✅ Success: {analytics.get("success",0)}
❌ Failed: {analytics.get("failed",0)}
🚫 Removed: {analytics.get("removed",0)}

🕒 Last: {analytics.get("last_run","-")}
""".strip()

        await safe_send_message(client, event.sender_id, msg)

    logger.info("Handlers registered")
    # ==========================================================
# RUN SENDER PIPELINE
# ==========================================================

async def run_sender_pipeline(
    client: TelegramClient,
    user_manager: UserManager
):

    logger.info("🚀 Starting Sender Pipeline")

    users = await user_manager.load_users()

    if not users:
        logger.warning("No users found")
        return

    # ✅ DELTA SYSTEM ACTIVE
    files = get_changed_files(get_output_files())

    # ❗ FIX: این بخش قبلاً indentation خراب داشت
    if not files:

        logger.info("ℹ️ no changed files")

        return

    logger.info(f"Users={len(users)} | Files={len(files)}")

    success = 0
    failed = 0
    removed = 0

    try:

        results = await process_batch(
            client=client,
            users=users,
            files=files,
            user_manager=user_manager
        )

        for r in results:

            if r == "success":
                success += 1

            elif r == "removed":
                removed += 1

            else:
                failed += 1

    except Exception as e:
        logger.exception(f"Pipeline error: {e}")

    # ======================================================
    # SAVE ANALYTICS
    # ======================================================

    AnalyticsManager().save(
        success=success,
        failed=failed,
        removed=removed
    )

    logger.info("━━━━━━━━━━━━━━━━━━")
    logger.info(f"Success={success}")
    logger.info(f"Failed={failed}")
    logger.info(f"Removed={removed}")
    logger.info("━━━━━━━━━━━━━━━━━━")


# ==========================================================
# CLIENT FACTORY
# ==========================================================

async def create_client():

    logger.info("Connecting Telegram...")

    client = TelegramClient(
        "bot_session",
        API_ID,
        API_HASH
    )

    await client.start(bot_token=BOT_TOKEN)

    logger.info("Telegram Connected")

    return client


# ==========================================================
# MAIN LOOP (FIXED - PRODUCTION SAFE)
# ==========================================================

async def main():

    logger.info("🚀 Bot Starting...")

    start_time = time.time()

    client = None

    try:

        # INIT MANAGER
        user_manager = UserManager()

        # CONNECT
        client = await create_client()

        # REGISTER HANDLERS
        await register_handlers(client, user_manager)

        logger.info("Handlers Ready")

        # SMALL DELAY FOR TELEGRAM STABILITY
        await asyncio.sleep(2)

        # ==================================================
        # RUN PIPELINE ON START
        # ==================================================

        await run_sender_pipeline(client, user_manager)

        # ==================================================
        # KEEP BOT ALIVE (IMPORTANT FIX)
        # ==================================================
        logger.info("Bot is now online...")

        # ❗ FIX: قبلاً فقط sleep بود → باعث خاموشی ربات می‌شد
        await client.run_until_disconnected()

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")

    except Exception as e:
        logger.exception(f"Fatal error: {e}")

    finally:

        logger.info("Graceful shutdown...")

        try:
            if client:
                await client.disconnect()
        except Exception as e:
            logger.warning(f"Disconnect error: {e}")

        elapsed = round(time.time() - start_time, 2)

        logger.info(f"Exit after {elapsed}s")
        logger.info("🏁 Bot stopped")


# ==========================================================
# ENTRYPOINT
# ==========================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.warning("Stopped manually")

    except Exception as e:
        logger.exception(f"Crash: {e}")

    finally:
        logger.info("Cleanup done")