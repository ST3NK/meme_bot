import os
import random
import requests
from datetime import datetime, timezone

# Hand-pick your comedy subs here.
SUBREDDITS = ["dankmemes", "comedyheaven", "okbuddyretard"]

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
# Status messages go here if set; otherwise they fall back to the main webhook.
STATUS_WEBHOOK_URL = os.environ.get("STATUS_WEBHOOK_URL", WEBHOOK_URL)
# Reddit blocks default/blank user agents — this string just needs to be unique-ish.
HEADERS = {"User-Agent": "discord-meme-poster/1.0 (by u/Electrical-Baker2368)"}

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif")


def send_status(text):
    """Post a heartbeat line so you know the run happened."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        requests.post(STATUS_WEBHOOK_URL, json={"content": f"[{stamp}] {text}"}, timeout=15)
    except Exception as e:
        print(f"status post failed: {e}")


def fetch_image_posts(subreddit):
    """Return a list of (title, image_url, permalink) for image posts in a sub."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json?t=day&limit=50"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    posts = resp.json()["data"]["children"]

    candidates = []
    for p in posts:
        d = p["data"]
        if d.get("stickied"):
            continue
        link = d.get("url_overridden_by_dest") or d.get("url", "")
        if link.lower().endswith(IMAGE_EXTS):
            candidates.append((d["title"], link, d["permalink"]))
    return candidates


def main():
    # Pool candidates from every subreddit, tagging each with its source.
    pool = []
    for sub in SUBREDDITS:
        try:
            for title, image_url, permalink in fetch_image_posts(sub):
                pool.append((title, image_url, permalink, sub))
        except Exception as e:
            print(f"skip r/{sub}: {e}")

    if not pool:
        print("no image posts found in any subreddit this run")
        send_status("⚠️ ran, but found no image posts in any subreddit")
        return

    title, image_url, permalink, sub = random.choice(pool)

    content = (
        f"{title}\n\n"
        f"— from r/{sub} · https://reddit.com{permalink}"
    )
    payload = {
        "content": content[:1900],
        "embeds": [{"image": {"url": image_url}}],
    }
    r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
    r.raise_for_status()

    print(f"posted from r/{sub}: {title}")
    send_status(f"✅ ran, posted a meme from r/{sub}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Something broke mid-run — report it so a silent failure doesn't slip by.
        print(f"run failed: {e}")
        send_status(f"❌ run failed: {e}")
        raise  # re-raise so the Actions run also shows red
