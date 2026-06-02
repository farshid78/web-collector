# Web Collector Bot

ربات جمع‌آوری و ارسال خودکار کانفیگ‌ها

## Features

- Telegram scraper
- Subscription fetch
- Country split configs
- Auto sender bot
- GitHub Actions automation

## Setup

Install:

```bash
pip install -r requirements.txt
```

Secrets:

```env
API_ID=
API_HASH=
SESSION_STRING=
TELEGRAM_BOT_TOKEN=
```

Run:

```bash
python scraper/scraper.py
python bot.py
```

## Output

configs.txt

configs_IR.txt

configs_US.txt

subscription_links.txt