import os
import random
import requests

# Swap these for the comedy subs you actually want. Hand-pick them —
# don't grab a generic "nsfw" preset or you'll get the sexual stuff you said you don't want.
SUBREDDITS = ["dankmemes", "comedyheaven", "okbuddyretard"]

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
# Reddit blocks default/blank user agents — this string just needs to be unique-ish.
HEADERS = {"User-Agent": "discord-meme-poster/1.0 (by u/yourusername)"}

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif")


def fetch_image_post(subreddit):
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
    subs = SUBREDDITS[:]
    random.shuffle(subs)

    for sub in subs:
        try:
            candidates = fetch_image_post(sub)
        except Exception as e:
            print(f"skip r/{sub}: {e}")
            continue
        if candidates:
            title, image_url, permalink = random.choice(candidates)
            payload = {
                "embeds": [{
                    "title": title[:250],
                    "url": f"https://reddit.com{permalink}",
                    "image": {"url": image_url},
                    "footer": {"text": f"r/{sub}"},
                }]
            }
            r = requests.post(WEBHOOK_URL, json=payload, timeout=15)
            r.raise_for_status()
            print(f"posted from r/{sub}: {title}")
            return

    print("no image posts found in any subreddit this run")


if __name__ == "__main__":
    main()
