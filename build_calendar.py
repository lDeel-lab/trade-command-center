"""Build site/data/calendar.json — the economic calendar.

Source: ForexFactory's free weekly calendar JSON (faireconomy.media mirror),
this week + next week. No API key needed. Each event:
  {t (ms), title, country (currency code), impact (High/Medium/Low/Holiday),
   forecast, previous}

Investing.com has no free API and forbids scraping, so this uses the
long-standing free FF feed instead — same events, same times.

Usage: python build_calendar.py [--mock]
"""

import json, os, sys, time
import datetime as dt

OUT = "site/data/calendar.json"
FEEDS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
]


def fetch(url):
    import requests
    r = requests.get(url, timeout=30,
                     headers={"User-Agent": "trade-command-center/1.0"})
    r.raise_for_status()
    return r.json()


def parse_when(s):
    """FF dates look like 2026-08-31T08:30:00-04:00."""
    try:
        return int(dt.datetime.fromisoformat(s).timestamp() * 1000)
    except Exception:
        return None


def collect():
    events, seen = [], set()
    for url in FEEDS:
        try:
            rows = fetch(url)
        except Exception as e:  # noqa: BLE001 — one dead feed never kills the build
            print(f"  ! {url}: {e}", file=sys.stderr)
            continue
        for r in rows:
            t = parse_when(r.get("date", ""))
            title = (r.get("title") or "").strip()
            if not t or not title:
                continue
            key = (t, title, r.get("country"))
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "t": t,
                "title": title[:120],
                "country": (r.get("country") or "").upper(),
                "impact": r.get("impact") or "Low",
                "forecast": (r.get("forecast") or "").strip(),
                "previous": (r.get("previous") or "").strip(),
            })
    events.sort(key=lambda x: x["t"])
    return events


def mock_events():
    now = int(time.time() * 1000)
    hour = 3600e3
    rows = [
        (now + 0.7 * hour, "CPI y/y", "USD", "High", "3.1%", "3.3%"),
        (now + 3 * hour, "FOMC Member Speaks", "USD", "Medium", "", ""),
        (now + 6 * hour, "BoE Gov Bailey Speaks", "GBP", "High", "", ""),
        (now + 26 * hour, "Non-Farm Payrolls", "USD", "High", "180K", "142K"),
        (now + 27 * hour, "Unemployment Rate", "USD", "High", "4.2%", "4.3%"),
        (now + 30 * hour, "GDP q/q", "EUR", "Medium", "0.3%", "0.2%"),
        (now + 50 * hour, "BoJ Policy Rate", "JPY", "High", "0.75%", "0.50%"),
        (now + 75 * hour, "Retail Sales m/m", "GBP", "Medium", "0.4%", "-0.2%"),
        (now + 90 * hour, "Bank Holiday", "CNY", "Holiday", "", ""),
        (now + 100 * hour, "Crude Oil Inventories", "USD", "Low", "", "-2.4M"),
    ]
    return [{"t": int(t), "title": ti, "country": c, "impact": i,
             "forecast": f, "previous": p} for t, ti, c, i, f, p in rows]


def main():
    events = mock_events() if "--mock" in sys.argv else collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"generated": int(time.time() * 1000), "events": events},
                  fh, separators=(",", ":"))
    print(f"Wrote {OUT} ({len(events)} events)")


if __name__ == "__main__":
    main()
