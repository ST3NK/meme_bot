curl -sS -o /dev/null -w "%{http_code}\n" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36" \
  -H "accept-language: en-US,en;q=0.9" \
  "https://www.reddit.com/r/dankmemes/top/.rss?t=day&limit=50"
