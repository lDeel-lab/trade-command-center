"""Build per-tab market data JSONs for the Trade Command Center.

For every non-crypto instrument, fetches multi-timeframe candles from Yahoo
Finance and writes site/data/<tab>.json:
  {generated, instruments: [{id, name, cls, region, sector, ig, tv,
                             candles: {"15m": [[t,o,h,l,c,v],...], ...}}]}
Timeframes: 15m, 30m, 1H, 4H (resampled from 1H), D, W, Q (resampled from
monthly). 5m is deliberately omitted for these markets — intraday scope starts
at 15m; crypto keeps 5m live client-side.

Usage:  python build_markets.py            (live)
        python build_markets.py --mock     (synthetic data, for offline testing)
"""

import json, math, os, sys, time
import pandas as pd
from universe import FILES, all_instruments

OUT = "site/data"
INTERVALS = [  # (tfKey, yf interval, period, keep_bars)
    ("15m", "15m", "5d",  120),
    ("30m", "30m", "10d", 120),
    ("1H",  "1h",  "60d", 200),
    ("D",   "1d",  "2y",  250),
    ("W",   "1wk", "10y", 200),
    ("M",   "1mo", "max", 200),   # source for Q
]

def r5(x):
    return float(f"{x:.6g}") if isinstance(x, float) and math.isfinite(x) else None

def df_to_rows(df, keep):
    rows = []
    for t, r in df.iterrows():
        if pd.isna(r["Close"]) or pd.isna(r["Open"]):
            continue
        ts = int(t.timestamp() * 1000) if hasattr(t, "timestamp") else int(t)
        v = 0 if pd.isna(r.get("Volume")) else float(r["Volume"])
        rows.append([ts, r5(float(r["Open"])), r5(float(r["High"])),
                     r5(float(r["Low"])), r5(float(r["Close"])), r5(v)])
    return rows[-keep:]

def resample_rows(rows, n):
    """Aggregate groups of n candles (4H from 1H, Q from M), anchored to the
    END so the last bar is always the current one."""
    out = []
    grouped, i = [], len(rows)
    while i > 0:
        grouped.append(rows[max(0, i-n):i]); i -= n
    grouped.reverse()
    for g in grouped:
        out.append([g[0][0], g[0][1], max(x[2] for x in g), min(x[3] for x in g),
                    g[-1][4], r5(sum(x[5] or 0 for x in g))])
    return out

def quarter_rows(monthly):
    out, cur, curq = [], None, None
    for m in monthly:
        d = pd.Timestamp(m[0], unit="ms", tz="UTC")
        q = (d.year, (d.month - 1) // 3)
        if q != curq:
            if cur: out.append(cur)
            cur, curq = list(m), q
        else:
            cur[2] = max(cur[2], m[2]); cur[3] = min(cur[3], m[3])
            cur[4] = m[4]; cur[5] = r5((cur[5] or 0) + (m[5] or 0))
    if cur: out.append(cur)
    return out[-60:]

def mock_rows(seed, tf_ms, n, base):
    import random
    rng = random.Random(seed)
    px, rows, now = base, [], int(time.time() * 1000)
    drift = (rng.random() - 0.45) * 0.004
    for i in range(n):
        sq = 0.3 if n - 40 < i < n - 20 else 1
        o = px; c = px * (1 + (rng.random() - 0.5) * 0.02 * sq + drift)
        h = max(o, c) * (1 + rng.random() * 0.008 * sq)
        l = min(o, c) * (1 - rng.random() * 0.008 * sq)
        v = (0.5 + rng.random()) * (4 if i == n - 3 else 1) * 1e6
        rows.append([now - (n - i) * tf_ms, r5(o), r5(h), r5(l), r5(c), r5(v)])
        px = c
    return rows

def build_mock(inst):
    seed = sum(ord(c) for c in inst["id"])
    base = 50 + (seed % 400) * 10.0
    ms = {"15m": 9e5, "30m": 18e5, "1H": 36e5, "D": 864e5, "W": 6048e5, "M": 26e8}
    candles = {k: mock_rows(seed * 7 + i, int(ms[k]), 160 if k != "M" else 96, base)
               for i, k in enumerate(ms)}
    candles["4H"] = resample_rows(candles["1H"], 4)
    candles["Q"] = quarter_rows(candles.pop("M"))
    return candles

def build_live(symbols):
    """Fetch all intervals for a list of symbols; returns {sym: {tf: rows}}."""
    import yfinance as yf
    out = {s: {} for s in symbols}
    for tfKey, iv, period, keep in INTERVALS:
        try:
            df = yf.download(symbols, interval=iv, period=period,
                             group_by="ticker", threads=True, progress=False,
                             auto_adjust=True)
        except Exception as e:
            print(f"  ! {iv}: {e}", file=sys.stderr); continue
        for s in symbols:
            try:
                sub = df[s].dropna(how="all") if len(symbols) > 1 else df.dropna(how="all")
                rows = df_to_rows(sub, keep)
                if rows: out[s][tfKey] = rows
            except Exception:
                pass
        time.sleep(1)
    for s in symbols:
        if "1H" in out[s]: out[s]["4H"] = resample_rows(out[s]["1H"], 4)[-160:]
        if "M" in out[s]: out[s]["Q"] = quarter_rows(out[s].pop("M"))
        else: out[s].pop("M", None)
    return out

def main():
    mock = "--mock" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    meta = {"generated": int(time.time() * 1000), "files": list(FILES.keys())}
    for fkey in FILES:
        insts = [i for i in all_instruments() if i["file"] == fkey]
        print(f"── {fkey} ({len(insts)} instruments)")
        if mock:
            data = {i["id"]: build_mock(i) for i in insts}
        else:
            data = build_live([i["id"] for i in insts])
        payload = {"generated": int(time.time() * 1000), "instruments": []}
        for i in insts:
            candles = data.get(i["id"], {})
            if not candles:
                print(f"  ✗ {i['name']}: no data"); continue
            payload["instruments"].append({**{k: i[k] for k in
                ("id", "name", "cls", "region", "sector", "ig", "tv")},
                "candles": candles})
        with open(f"{OUT}/{fkey}.json", "w") as fh:
            json.dump(payload, fh, separators=(",", ":"))
        print(f"  ✓ {len(payload['instruments'])} written")
    with open(f"{OUT}/meta.json", "w") as fh:
        json.dump(meta, fh)

if __name__ == "__main__":
    main()
