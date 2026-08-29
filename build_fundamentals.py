"""Build site/data/fundamentals.json — fundamentals + flags + score per instrument.

Stocks get Yahoo fundamentals (PE, forward PE, EPS, growth, margins, D/E,
dividend, analyst target) scored -3…+3 with plain-English flags.
Indices / FX / commodities get their class description and a neutral score —
their "fundamentals" are the macro calendar, handled by the news layer.

Usage: python build_fundamentals.py [--mock]
"""

import json, os, sys, time
from universe import all_instruments, STATIC_DESC

OUT = "site/data/fundamentals.json"

def score_stock(f):
    flags, score = [], 0
    fpe, pe = f.get("fpe"), f.get("pe")
    if fpe:
        if fpe < 14: flags.append(f"✓ forward P/E {fpe:.1f} — cheap vs the market"); score += 1
        elif fpe < 22: flags.append(f"forward P/E {fpe:.1f} — around market average")
        elif fpe < 35: flags.append(f"forward P/E {fpe:.1f} — priced for growth"); score -= 0
        else: flags.append(f"⚠ forward P/E {fpe:.1f} — expensive; needs flawless delivery"); score -= 1
        if pe and fpe < pe * 0.85:
            flags.append("✓ forward P/E well below trailing — earnings expected to grow"); score += 1
    eg, rg = f.get("epsG"), f.get("revG")
    if eg is not None:
        if eg > 0.15: flags.append(f"✓ EPS growth {eg*100:.0f}%"); score += 1
        elif eg < 0: flags.append(f"⚠ EPS shrinking ({eg*100:.0f}%)"); score -= 1
    if rg is not None and rg > 0.10:
        flags.append(f"✓ revenue growth {rg*100:.0f}%"); score += 1
    m = f.get("margin")
    if m is not None:
        if m > 0.18: flags.append(f"✓ net margin {m*100:.0f}% — quality business"); score += 1
        elif m < 0.05: flags.append(f"thin net margin {m*100:.1f}%")
    de = f.get("de")
    if de is not None and de > 150:
        flags.append(f"⚠ debt/equity {de:.0f}% — leveraged balance sheet"); score -= 1
    dy = f.get("divY")
    if dy: flags.append(f"dividend yield {dy:.1f}%")
    tgt, px = f.get("target"), f.get("price")
    if tgt and px:
        up = (tgt / px - 1) * 100
        if up > 15: flags.append(f"✓ analyst mean target {up:+.0f}% above price"); score += 1
        elif up < -5: flags.append(f"⚠ price already {-up:.0f}% ABOVE the mean analyst target"); score -= 1
    return max(-3, min(3, score)), flags

def fetch_stock(sym):
    import yfinance as yf
    info = yf.Ticker(sym).info or {}
    g = info.get
    return {
        "desc": (g("longBusinessSummary") or "")[:420],
        "pe": g("trailingPE"), "fpe": g("forwardPE"), "eps": g("trailingEps"),
        "epsG": g("earningsGrowth"), "revG": g("revenueGrowth"),
        "margin": g("profitMargins"), "de": g("debtToEquity"),
        "divY": (g("dividendYield") or 0) * (100 if (g("dividendYield") or 0) < 1 else 1) or None,
        "target": g("targetMeanPrice"), "price": g("currentPrice") or g("regularMarketPrice"),
        "rec": g("recommendationKey"), "mcap": g("marketCap"),
    }

def main():
    mock = "--mock" in sys.argv
    out = {}
    for inst in all_instruments():
        sid = inst["id"]
        if inst["cls"] != "stock":
            out[sid] = {"cls": inst["cls"], "desc": STATIC_DESC[inst["cls"]],
                        "score": 0, "flags": []}
            continue
        if mock:
            f = {"desc": f"{inst['name']} — mock description for offline preview. "
                 f"{inst['sector']} company in {inst['region']}.",
                 "pe": 24.0, "fpe": 18.5, "eps": 6.1, "epsG": 0.18, "revG": 0.12,
                 "margin": 0.21, "de": 80.0, "divY": 1.4, "target": 120.0,
                 "price": 100.0, "rec": "buy", "mcap": 5e11}
        else:
            try:
                f = fetch_stock(sid)
                time.sleep(0.4)   # be polite to Yahoo
            except Exception as e:
                print(f"  ! {sid}: {e}", file=sys.stderr)
                out[sid] = {"cls": "stock", "desc": "", "score": 0,
                            "flags": ["fundamentals unavailable this run"]}
                continue
        score, flags = score_stock(f)
        f.update({"cls": "stock", "score": score, "flags": flags,
                  "sector": inst["sector"], "region": inst["region"]})
        out[sid] = {k: v for k, v in f.items() if v is not None}
        print(f"  ✓ {inst['name']}: score {score:+d}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump({"generated": int(time.time() * 1000), "instruments": out},
                  fh, separators=(",", ":"))
    print(f"Wrote {OUT} ({len(out)} instruments)")

if __name__ == "__main__":
    main()
