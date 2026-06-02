from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# پورت SOCKS5 پروفایل Reality
SOCKS5_HOST = "127.0.0.1"
SOCKS5_PORT = 10808  # همونی که گفتی

proxy_settings = {
    "proxy_type": "socks5",
    "addr": SOCKS5_HOST,
    "port": SOCKS5_PORT,
}

print(f"Using SOCKS5 proxy: {SOCKS5_HOST}:{SOCKS5_PORT}")

api_id = int(input("Enter API_ID: ").strip())
api_hash = input("Enter API_HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash, proxy=proxy_settings) as client:
    print("\nYour SESSION_STRING:\n")
    print(client.session.save())
    print("\nCopy this string and save it safely.")
