import os
import random
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
STATUS_WEBHOOK_URL = os.environ.get("STATUS_WEBHOOK_URL", WEBHOOK_URL)

MEMES_FILE = "memes.txt"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def send_status(text):
    """Post a heartbeat line so you know the run happened."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        requests.post(STATUS_WEBHOOK_URL, json={"content": f"[{stamp}] {text}"}, timeout=15)
    except Exception as e:
        print(f"status post failed: {e}")


def load_pool(path):
    """Read memes.txt: one URL per line, blank lines and #-comments ignored."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []
    pool = []
    for line in lines:
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        pool.append(url)
    return pool


def main():
    pool = load_pool(MEMES_FILE)
    if not pool:
        print(f"{MEMES_FILE} is empty or missing")
        send_status(f"⚠️ ran, but {MEMES_FILE} has no memes to post")
        return

    url = random.choice(pool)

    # Direct image links render cleanly inside an embed. Anything else (an imgur
    # page link, etc.) goes out as plain text so Discord can try to unfurl it.
    clean = url.lower().split("?")[0]  # ignore ?width=… query strings
    if clean.endswith(IMAGE_EXTS):
        payload = {"embeds": [{"image": {"url": url}}]}
    else:
        payload = {"content": url}

    r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    r.raise_for_status()

    print(f"posted: {url}")
    send_status(f"✅ ran, posted a meme ({len(pool)} in pool)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"run failed: {e}")
        send_status(f"❌ run failed: {e}")
        raise
