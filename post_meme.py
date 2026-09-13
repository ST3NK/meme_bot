import os
import random
import requests
import feedparser
from datetime import datetime, timezone

# Each sub maps to its own rss.app bridge feed URL.
# Bridge fetches Reddit from rss.app's IP, so GitHub Actions never touches Reddit directly.
SUBREDDIT_FEEDS = {
    "dankmemes": "https://rss.app/feeds/keHUQ03lfmJ4jFeH.xml",
    "comedyheaven": "https://rss.app/feeds/fsa21IAxOlww0exA.xml",   # <-- paste your comedyheaven feed
    "okbuddyretard": "https://rss.app/feeds/keHUQ03lfmJ4jFeH.xml",  # <-- paste your okbuddyretard feed
}

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
# Status messages go here if set; otherwise they fall back to the main webhook.
STATUS_WEBHOOK_URL = os.environ.get("STATUS_WEBHOOK_URL", WEBHOOK_URL)
# We're hitting rss.app, not Reddit, so no special headers are needed — this is just polite.
HEADERS = {"User-Agent": "discord-meme-poster/1.0"}


def send_status(text):
    """Post a heartbeat line so you know the run happened."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    try:
        requests.post(STATUS_WEBHOOK_URL, json={"content": f"[{stamp}] {text}"}, timeout=15)
    except Exception as e:
        print(f"status post failed: {e}")


def fetch_image_posts(subreddit, feed_url):
    """Return a list of (title, image_url, post_url) for image posts, via the sub's rss.app feed."""
    resp = requests.get(feed_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)

    candidates = []
    for entry in feed.entries:
        title = entry.get("title", "")
        post_url = entry.get("link", "")  # full URL to the reddit comments page

        # rss.app puts the image in <media:content>; feedparser exposes it as
        # entry.media_content — a list of dicts, each with 'medium' and 'url'.
        image_url = None
        for media in entry.get("media_content", []):
            if media.get("medium") == "image" and media.get("url"):
                image_url = media["url"]
                break

        if image_url:
            candidates.append((title, image_url, post_url))
    return candidates


def main():
    # Pool candidates from every feed, tagging each with its source sub.
    pool = []
    for sub, feed_url in SUBREDDIT_FEEDS.items():
        try:
            for title, image_url, post_url in fetch_image_posts(sub, feed_url):
                pool.append((title, image_url, post_url, sub))
        except Exception as e:
            print(f"skip r/{sub}: {e}")

    if not pool:
        print("no image posts found in any feed this run")
        send_status("⚠️ ran, but found no image posts in any feed")
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
