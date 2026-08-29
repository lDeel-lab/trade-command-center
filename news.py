"""Hourly finance news digest → Telegram.

Pulls headlines from a configurable set of RSS feeds, drops anything
already posted (state/seen_news.json, committed back to the repo by the
workflow), groups the rest by category, and posts a compact digest.
If nothing new appeared since the last run, posts nothing.

Env vars required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
Optional: DRY_RUN=1 prints the digest instead of sending.
"""

import datetime as dt
import hashlib
import json
import os
import pathlib

import feedparser

from tg import esc, send

FEEDS = {
    "🌍 Markets & Macro": [
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",   # CNBC Top News
        "https://www.cnbc.com/id/20910258/device/rss/rss.html",    # CNBC Markets
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",  # MarketWatch
        "https://finance.yahoo.com/news/rssindex",                 # Yahoo Finance
        "http://feeds.bbci.co.uk/news/business/rss.xml",           # BBC Business
        "https://www.investing.com/rss/news_25.rss",               # Investing.com markets
    ],
    "💱 FX & Central Banks": [
        "https://www.forexlive.com/feed/news",
    ],
    "₿ Crypto": [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
    ],
}

STATE = pathlib.Path("state/seen_news.json")
MAX_PER_CATEGORY = 6      # keep each digest readable
MAX_AGE_HOURS = 12        # ignore items older than this
KEEP_SEEN = 3000          # cap the de-dup memory


def load_seen() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_seen(seen: dict) -> None:
    trimmed = dict(sorted(seen.items(), key=lambda kv: kv[1])[-KEEP_SEEN:])
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(trimmed, indent=0))


def item_id(entry) -> str:
    basis = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def entry_time(entry) -> dt.datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return dt.datetime(*t[:6], tzinfo=dt.timezone.utc)
    return None


def collect() -> tuple[dict[str, list[dict]], dict]:
    seen = load_seen()
    now = dt.datetime.now(dt.timezone.utc)
    fresh: dict[str, list[dict]] = {}
    for category, urls in FEEDS.items():
        items = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception as exc:  # noqa: BLE001 — one dead feed never kills the digest
                print(f"  ! {url}: {exc}")
                continue
            source = (feed.feed.get("title") or url.split("/")[2]).strip()
            for entry in feed.entries[:20]:
                uid = item_id(entry)
                if uid in seen:
                    continue
                when = entry_time(entry)
                if when and (now - when) > dt.timedelta(hours=MAX_AGE_HOURS):
                    continue
                title = " ".join(entry.get("title", "").split())
                link = entry.get("link", "")
                if not title or not link:
                    continue
                seen[uid] = now.isoformat()
                items.append({"title": title, "link": link,
                              "source": source, "when": when or now})
        items.sort(key=lambda x: x["when"], reverse=True)
        # de-dup near-identical headlines across sources
        picked, used = [], set()
        for it in items:
            key = it["title"].lower()[:60]
            if key in used:
                continue
            used.add(key)
            picked.append(it)
            if len(picked) >= MAX_PER_CATEGORY:
                break
        fresh[category] = picked
    return fresh, seen


def latest_headlines(max_age_hours: int = 24,
                     per_category: int = 10) -> list[dict]:
    """Latest headlines regardless of seen-state — for the dashboard's News tab.

    Returns flat rows: {cat, title, link, source, time}.
    """
    now = dt.datetime.now(dt.timezone.utc)
    out: list[dict] = []
    for category, urls in FEEDS.items():
        items = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception:  # noqa: BLE001
                continue
            source = (feed.feed.get("title") or url.split("/")[2]).strip()
            for entry in feed.entries[:20]:
                when = entry_time(entry)
                if when and (now - when) > dt.timedelta(hours=max_age_hours):
                    continue
                title = " ".join(entry.get("title", "").split())
                link = entry.get("link", "")
                if title and link:
                    items.append({"title": title, "link": link,
                                  "source": source, "when": when or now})
        items.sort(key=lambda x: x["when"], reverse=True)
        used: set[str] = set()
        for it in items:
            key = it["title"].lower()[:60]
            if key in used:
                continue
            used.add(key)
            out.append({"cat": category, "title": it["title"],
                        "link": it["link"], "source": it["source"],
                        "time": it["when"].strftime("%H:%M UTC")})
            if sum(1 for o in out if o["cat"] == category) >= per_category:
                break
    return out


def build_message(fresh: dict[str, list[dict]]) -> str | None:
    total = sum(len(v) for v in fresh.values())
    if total == 0:
        return None
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%H:%M UTC · %d %b")
    parts = [f"📰 <b>MARKET NEWS DIGEST</b> — {stamp}"]
    for category, items in fresh.items():
        if not items:
            continue
        lines = [f"<b>{esc(category)}</b>"]
        for it in items:
            lines.append(f"• <a href=\"{it['link']}\">{esc(it['title'])}</a> "
                         f"<i>({esc(it['source'])})</i>")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def main() -> None:
    fresh, seen = collect()
    msg = build_message(fresh)
    if msg is None:
        print("No new headlines — nothing posted.")
        return
    if os.environ.get("DRY_RUN"):
        print(msg)
    else:
        send(msg)
        total = sum(len(v) for v in fresh.values())
        print(f"Posted digest with {total} headlines.")
    save_seen(seen)


if __name__ == "__main__":
    main()
