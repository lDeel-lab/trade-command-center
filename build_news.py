"""Build site/data/news.json — global finance news, hierarchically tagged.

Every item: {t, title, link, src, domain, sector, region, instruments[]}
  domain : Crypto | Stocks | Commodities | FX | Macro
  sector : for Stocks items — Technology / Energy / Financials / … (from the
           matched instrument, or keyword rules)
  region : US / UK / Europe / India / Japan / ChinaHK / Global
  instruments: ids of matched instruments (name/alias found in the headline)

Sources: the global wires in news.py, regional Google News RSS queries, and
Yahoo per-ticker feeds batched ~20 tickers per request.

Usage: python build_news.py [--mock]
"""

import datetime as dt
import hashlib, json, os, re, sys, time

from universe import all_instruments
from news import FEEDS as GLOBAL_FEEDS, entry_time, transmission_for

OUT = "site/data/news.json"
MAX_ITEMS = 300
MAX_AGE_H = 36

REGIONAL_FEEDS = {
    "India": ["https://news.google.com/rss/search?q=nifty+OR+sensex+OR+%22indian+stocks%22&hl=en-IN&gl=IN&ceid=IN:en"],
    "Japan": ["https://news.google.com/rss/search?q=nikkei+OR+%22japan+stocks%22+OR+%22bank+of+japan%22&hl=en&gl=US&ceid=US:en"],
    "ChinaHK": ["https://news.google.com/rss/search?q=%22hang+seng%22+OR+%22china+stocks%22+OR+%22hong+kong+stocks%22&hl=en&gl=US&ceid=US:en"],
    "UK": ["https://news.google.com/rss/search?q=%22ftse%22+OR+%22bank+of+england%22&hl=en-GB&gl=GB&ceid=GB:en"],
    "Europe": ["https://news.google.com/rss/search?q=%22dax%22+OR+%22ecb%22+OR+%22euro+zone%22&hl=en&gl=US&ceid=US:en"],
    "Emerging": ["https://news.google.com/rss/search?q=%22emerging+markets%22+OR+%22brazil+stocks%22+OR+%22south+africa+economy%22+OR+%22latin+america%22+OR+lithium+OR+%22copper+mining%22&hl=en&gl=US&ceid=US:en"],
}

DOMAIN_BY_CAT = {"🌍 Markets & Macro": "Macro", "💱 FX & Central Banks": "FX",
                 "₿ Crypto": "Crypto"}
KW = [  # (regex, domain, sector, region)
    (r"\b(bitcoin|btc|ethereum|crypto|solana|stablecoin|defi|etf inflow)\b", "Crypto", "", ""),
    (r"\b(oil|opec|crude|brent|wti|natural gas|gold|silver|copper|wheat|cocoa|coffee)\b", "Commodities", "", ""),
    (r"\b(fed|fomc|powell|cpi|inflation|rate cut|rate hike|treasury|jobs report|payrolls|gdp)\b", "Macro", "", "US"),
    (r"\b(ecb|lagarde|euro ?zone|bundesbank)\b", "Macro", "", "Europe"),
    (r"\b(bank of england|boe|ftse|gilt)\b", "Macro", "", "UK"),
    (r"\b(bank of japan|boj|yen|nikkei)\b", "Macro", "", "Japan"),
    (r"\b(rbi|nifty|sensex|rupee)\b", "Macro", "", "India"),
    (r"\b(pboc|hang seng|yuan|renminbi)\b", "Macro", "", "ChinaHK"),
    (r"\b(emerging markets?|brazil|mexico|argentina|chile|colombia|peru|south africa"
     r"|johannesburg|bovespa|indonesia|turkey|kazakhstan|latin america)\b",
     "Macro", "", "Emerging"),
    (r"\b(dollar|eur/usd|gbp/usd|forex|currency)\b", "FX", "", ""),
    (r"\b(earnings|profit|revenue|guidance|shares|stock|ipo|dividend|buyback)\b", "Stocks", "", ""),
]

def alias_index():
    idx = []
    for i in all_instruments():
        terms = {i["name"].lower()} | {a.lower() for a in i["aliases"]}
        idx.append((i, [t for t in terms if len(t) >= 3]))
    return idx

ALIASES = alias_index()

def tag(title):
    tl = " " + title.lower() + " "
    matched = []
    for inst, terms in ALIASES:
        if any(re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", tl) for t in terms):
            matched.append(inst)
    domain = sector = region = ""
    if matched:
        m = matched[0]
        domain = {"stock": "Stocks", "index": "Macro", "fx": "FX",
                  "commodity": "Commodities"}[m["cls"]]
        sector = m["sector"] if m["cls"] == "stock" else ""
        region = m["region"]
    if not domain:
        for rx, d, s, r in KW:
            if re.search(rx, tl):
                domain, sector, region = d, s, r; break
    return domain or "Macro", sector, region or "Global", [m["id"] for m in matched[:4]]

def collect():
    import feedparser
    now = dt.datetime.now(dt.timezone.utc)
    items, seen = [], set()
    def add_feed(url, fallback_region=""):
        try:
            feed = feedparser.parse(url)
        except Exception:
            return
        src = (feed.feed.get("title") or url.split("/")[2]).strip()[:40]
        for e in feed.entries[:25]:
            title = " ".join(e.get("title", "").split())
            link = e.get("link", "")
            if not title or not link: continue
            when = entry_time(e) or now
            if (now - when) > dt.timedelta(hours=MAX_AGE_H): continue
            key = hashlib.sha256(title.lower()[:70].encode()).hexdigest()[:14]
            if key in seen: continue
            seen.add(key)
            domain, sector, region, insts = tag(title)
            if region == "Global" and fallback_region: region = fallback_region
            item = {"t": int(when.timestamp() * 1000), "title": title[:220],
                    "link": link, "src": src, "domain": domain,
                    "sector": sector, "region": region, "instruments": insts}
            tr = transmission_for(title)
            if tr: item["trade"] = tr
            items.append(item)
    for cat, urls in GLOBAL_FEEDS.items():
        for u in urls: add_feed(u)
    for region, urls in REGIONAL_FEEDS.items():
        for u in urls: add_feed(u, region)
    # Yahoo per-ticker feeds for stocks, batched
    stocks = [i["id"] for i in all_instruments() if i["cls"] == "stock"]
    for i in range(0, len(stocks), 20):
        batch = ",".join(stocks[i:i+20])
        add_feed(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={batch}&region=US&lang=en-US")
        time.sleep(0.3)
    items.sort(key=lambda x: x["t"], reverse=True)
    return items[:MAX_ITEMS]

def mock_items():
    now = int(time.time() * 1000)
    rows = [
        ("US CPI comes in at 3.1% vs 3.3% expected — dollar slides", "Macro", "", "US", ["DX-Y.NYB", "GC=F"]),
        ("Nvidia beats on earnings, guides Q4 revenue above estimates", "Stocks", "Technology", "US", ["NVDA"]),
        ("Shell announces $3bn buyback as profits top forecasts", "Stocks", "Energy", "UK", ["SHEL.L"]),
        ("OPEC+ weighs pausing output hikes amid demand doubts", "Commodities", "", "Global", ["CL=F", "BZ=F"]),
        ("Bank of Japan signals readiness to raise rates again", "Macro", "", "Japan", ["USDJPY=X", "^N225"]),
        ("Bitcoin ETF inflows hit weekly record of $1.2bn", "Crypto", "", "Global", []),
        ("Nifty hits record high as IT stocks rally on TCS results", "Stocks", "Technology", "India", ["TCS.NS", "^NSEI"]),
        ("Tencent revenue tops estimates on gaming rebound", "Stocks", "Technology", "ChinaHK", ["0700.HK"]),
        ("ECB minutes show split on the pace of further cuts", "Macro", "", "Europe", ["EURUSD=X", "^GDAXI"]),
        ("Gold breaks to fresh highs as real yields fall", "Commodities", "", "Global", ["GC=F"]),
        ("Ukrainian drone strike sets major Russian oil refinery ablaze", "Commodities", "", "Global", ["CL=F", "BZ=F"]),
    ]
    out = []
    for i, (t, d, s, r, ids) in enumerate(rows):
        item = {"t": now - i * 9e5, "title": t, "link": "https://example.com/" + str(i),
                "src": "MOCK", "domain": d, "sector": s, "region": r, "instruments": ids}
        tr = transmission_for(t)
        if tr: item["trade"] = tr
        out.append(item)
    return out

def main():
    items = mock_items() if "--mock" in sys.argv else collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"generated": int(time.time() * 1000), "items": items},
                  fh, separators=(",", ":"))
    print(f"Wrote {OUT} ({len(items)} items)")

if __name__ == "__main__":
    main()
