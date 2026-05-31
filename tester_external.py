import base64
import json
import socket

INPUT_FILE = "configs_final.txt"
OUTPUT_FILE = "configs_valid_external.txt"


def parse_vmess(cfg: str):
    """vmess:// را به host, port تبدیل می‌کند. اگر نشد → None"""
    try:
        raw = cfg.strip().replace("vmess://", "")
        # بعضی وقت‌ها padding ناقص است → با == جبران می‌کنیم
        padded = raw + "=" * (-len(raw) % 4)
        data = json.loads(base64.b64decode(padded).decode("utf-8"))
        host = data.get("add")
        port = int(data.get("port", 0))
        if not host or not port:
            return None
        return host, port
    except Exception:
        return None


def tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    """فقط چک می‌کند TCP به سرور باز می‌شود یا نه"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def filter_external():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} پیدا نشد")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    valid = []

    for cfg in lines:
        if cfg.startswith("vmess://"):
            parsed = parse_vmess(cfg)
            if not parsed:
                continue
            host, port = parsed
            if tcp_check(host, port):
                valid.append(cfg)
        else:
            # فعلاً بقیه پروتکل‌ها را رد می‌کنیم یا بعداً اضافه می‌کنی
            continue

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in valid:
            f.write(c + "\n")

    print(f"TOTAL: {len(lines)}  →  VALID_EXTERNAL: {len(valid)}")


if __name__ == "__main__":
    import os
    filter_external()
