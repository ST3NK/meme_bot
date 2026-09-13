import os
import re
import html
import random
import requests
import feedparser
from datetime import datetime, timezone

# Hand-pick your comedy subs here.
SUBREDDITS = ["dankmemes", "comedyheaven", "okbuddyretard"]

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
# Status messages go here if set; otherwise they fall back to the main webhook.
STATUS_WEBHOOK_URL = os.environ.get("STATUS_WEBHOOK_URL", WEBHOOK_URL)
# Reddit's RSS wants a browser-like UA + accept-language. Since your reachability
# test returned 200, this header set is what makes it pass.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
    "accept-language": "en-US,en;q=0.9",
}

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif")


def send_status(text):
    """Post a heartbeat line so you know the run happened."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        requests.post(STATUS_WEBHOOK_URL, json={"content": f"[{stamp}] {text}"}, timeout=15)
    except Exception as e:
        print(f"status post failed: {e}")


def fetch_image_posts(subreddit):
    """Return a list of (title, image_url, post_url) for image posts in a sub, via RSS."""
    url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day&limit=50"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)

    candidates = []
    for entry in feed.entries:
        title = entry.get("title", "")
        post_url = entry.get("link", "")  # full URL to the reddit comments page

        # The Atom <content> is an HTML blob. For a single-image post, the actual
        # image lives in the first <a href="...">[link]</a> inside it.
        content_html = ""
        if entry.get("content"):
            content_html = entry.content[0].value
        elif entry.get("summary"):
            content_html = entry.summary
        content_html = html.unescape(content_html)

        image_url = None
        for m in re.finditer(r'href="([^"]+)"', content_html):
            href = m.group(1)
            if href.lower().split("?")[0].endswith(IMAGE_EXTS):
                image_url = href
                break

        if image_url:
            candidates.append((title, image_url, post_url))
    return candidates


def main():
    # Pool candidates from every subreddit, tagging each with its source.
    pool = []
    for sub in SUBREDDITS:
        try:
            for title, image_url, post_url in fetch_image_posts(sub):
                pool.append((title, image_url, post_url, sub))
        except Exception as e:
            print(f"skip r/{sub}: {e}")

    if not pool:
        print("no image posts found in any subreddit this run")
        send_status("⚠️ ran, but found no image posts in any subreddit")
        return

    title, image_url, post_url, sub = random.choice(pool)

    content = (
        f"{title}\n\n"
        f"— from r/{sub} · {post_url}"
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
