"""Daily multi-market technical briefing → Telegram.

For every instrument in watchlist.py, pulls ~8 months of daily candles
from Yahoo Finance, computes EMA(20/50/200), RSI(14), MACD(12,26,9) and
ATR(14), scores trend + momentum confluence, and derives suggested
entry / stop-loss / TP1 / TP2 levels (ATR-based R-multiples) for
instruments with a clear bias. Neutral instruments get a one-liner.

These are systematic technical levels, not financial advice — the
briefing carries a disclaimer footer on every post.

Env vars required: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID.
Optional: DRY_RUN=1 prints the message instead of sending.
"""

import datetime as dt
import os
import sys
import time

import pandas as pd

from tg import esc, send
from watchlist import WATCHLIST, WEEKEND_SECTIONS

STALE_DAYS = 4          # skip instruments with no candle in the last N days
MIN_BARS = 60           # minimum history needed to compute indicators
SL_ATR = 1.5                      # stop distance in ATRs
TP1_R, TP2_R, TP3_R = 1.0, 2.0, 3.0  # take-profits in R multiples


# ---------------------------------------------------------------- indicators

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, pd.NA)
    return (100 - 100 / (1 + rs)).fillna(50)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["Close"].shift()
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


# ------------------------------------------------------------------ analysis

def analyze(df: pd.DataFrame) -> dict:
    """Score the latest bar. Returns a dict of everything the formatter needs."""
    close = df["Close"]
    e20, e50, e200 = ema(close, 20), ema(close, 50), ema(close, 200)
    r = rsi(close)
    macd_line = ema(close, 12) - ema(close, 26)
    macd_hist = macd_line - ema(macd_line, 9)
    a = atr(df)

    c = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    swing_hi = float(df["High"].iloc[-21:-1].max())
    swing_lo = float(df["Low"].iloc[-21:-1].min())

    checks = [
        ("Price above 50-day EMA", c > float(e50.iloc[-1])),
        ("EMA20 above EMA50 (short-term trend up)",
         float(e20.iloc[-1]) > float(e50.iloc[-1])),
        ("EMA50 above EMA200 (long-term trend up)",
         float(e50.iloc[-1]) > float(e200.iloc[-1])),
        ("RSI above 50 (bullish momentum)", float(r.iloc[-1]) > 50),
        ("MACD histogram positive", float(macd_hist.iloc[-1]) > 0),
        ("Closed higher than yesterday", c > prev),
    ]
    score = sum(1 if ok else -1 for _, ok in checks)  # -6 … +6

    if score >= 4:
        side = "BUY"
    elif score <= -4:
        side = "SELL"
    else:
        side = "NEUTRAL"

    risk = SL_ATR * float(a.iloc[-1])
    if side == "BUY":
        sl = c - risk
        tp1, tp2, tp3 = (c + r * risk for r in (TP1_R, TP2_R, TP3_R))
    elif side == "SELL":
        sl = c + risk
        tp1, tp2, tp3 = (c - r * risk for r in (TP1_R, TP2_R, TP3_R))
    else:
        sl = tp1 = tp2 = tp3 = None

    tail = 60  # series length for the dashboard charts
    return {
        "side": side,
        "strength": "strong" if abs(score) == 6 else "moderate",
        "score": score,
        "checks": [(label, bool(ok)) for label, ok in checks],
        "dates": [d.strftime("%d %b") for d in df.index[-tail:]],
        "close_series": [float(v) for v in close.iloc[-tail:]],
        "ema20_series": [float(v) for v in e20.iloc[-tail:]],
        "ema50_series": [float(v) for v in e50.iloc[-tail:]],
        "close": c,
        "chg_pct": (c / prev - 1) * 100 if prev else 0.0,
        "rsi": float(r.iloc[-1]),
        "above_e50": c > float(e50.iloc[-1]),
        "above_e200": c > float(e200.iloc[-1]),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "pullback": float(e20.iloc[-1]),
        "support": swing_lo,
        "resistance": swing_hi,
        "last_bar": df.index[-1],
    }


def fetch(symbol: str) -> pd.DataFrame | None:
    """Daily candles for ~8 months, with one retry. Returns None on failure."""
    import yfinance as yf

    for attempt in (1, 2):
        try:
            df = yf.Ticker(symbol).history(period="8mo", interval="1d",
                                           auto_adjust=True)
            if df is not None and len(df) >= MIN_BARS:
                return df
            if df is not None and not df.empty:
                return None  # too little history — skip quietly
        except Exception as exc:  # noqa: BLE001 — one instrument never kills the run
            if attempt == 2:
                print(f"  ! {symbol}: {exc}", file=sys.stderr)
        time.sleep(2 * attempt)
    return None


# ---------------------------------------------------------------- formatting

def fmt_price(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:,.2f}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


def fmt_instrument(name: str, x: dict) -> str:
    arrow = "▲" if x["chg_pct"] >= 0 else "▼"
    chg = f"{arrow}{abs(x['chg_pct']):.2f}%"
    if x["side"] == "NEUTRAL":
        return (f"⚪ <b>{esc(name)}</b> — NEUTRAL · {fmt_price(x['close'])} "
                f"({chg}) · RSI {x['rsi']:.0f} · "
                f"S {fmt_price(x['support'])} / R {fmt_price(x['resistance'])}")
    icon = "🟢" if x["side"] == "BUY" else "🔴"
    trend = []
    trend.append("above" if x["above_e50"] else "below")
    ema_note = f"{trend[0]} EMA50" + ("/200" if x["above_e50"] == x["above_e200"] else "")
    return (
        f"{icon} <b>{esc(name)}</b> — <b>{x['side']}</b> ({x['strength']}, "
        f"score {x['score']:+d}/6)\n"
        f"   {fmt_price(x['close'])} ({chg}) · RSI {x['rsi']:.0f} · {ema_note}\n"
        f"   🎯 Entry {fmt_price(x['close'])} · 🛑 SL {fmt_price(x['sl'])}\n"
        f"   💰 TP1 {fmt_price(x['tp1'])} · TP2 {fmt_price(x['tp2'])} · "
        f"TP3 {fmt_price(x['tp3'])}"
    )


DISCLAIMER = (
    "⚠️ <i>Systematic technical levels (EMA/RSI/MACD/ATR), generated "
    "automatically. Not financial advice — do your own research and manage "
    "risk. Stops are 1.5×ATR; TP1/TP2/TP3 are 1R/2R/3R.</i>"
)


def build_message(results: dict[str, list[tuple[str, dict]]]) -> str:
    today = dt.date.today().strftime("%A, %d %B %Y")
    parts = [f"📊 <b>DAILY MARKET BRIEFING</b>\n🗓 {today}\n"
             f"🟢 buy setup · 🔴 sell setup · ⚪ no edge today"]
    for section, rows in results.items():
        if not rows:
            continue
        actionable = [r for r in rows if r[1]["side"] != "NEUTRAL"]
        neutral = [r for r in rows if r[1]["side"] == "NEUTRAL"]
        lines = [f"━━━━━━━━━━━━━━━\n<b>{esc(section)}</b>"]
        for name, x in actionable + neutral:
            lines.append(fmt_instrument(name, x))
        parts.append("\n\n".join(lines))
    parts.append(DISCLAIMER)
    return "\n\n".join(parts)


# --------------------------------------------------------------------- main

def main() -> None:
    weekend = dt.date.today().weekday() >= 5
    results: dict[str, list[tuple[str, dict]]] = {}
    flat_rows: list[dict] = []
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=STALE_DAYS)

    for section, instruments in WATCHLIST.items():
        if weekend and section not in WEEKEND_SECTIONS:
            continue
        rows = []
        print(f"── {section}")
        for symbol, name in instruments:
            df = fetch(symbol)
            if df is None:
                print(f"  ✗ {name} ({symbol}): no data")
                continue
            last = df.index[-1]
            last = last.tz_localize("UTC") if last.tzinfo is None else last
            if last < cutoff:
                print(f"  ✗ {name}: stale (last bar {last.date()})")
                continue
            x = analyze(df)
            rows.append((name, x))
            flat_rows.append({"name": name, "symbol": symbol,
                              "section": section, "analysis": x})
            print(f"  ✓ {name}: {x['side']} {x['score']:+d}")
        results[section] = rows

    total = sum(len(v) for v in results.values())
    if total == 0:
        raise SystemExit("No data for any instrument — aborting without posting.")

    # The live dashboard is built and deployed by the data workflow; this job
    # only posts the daily Telegram briefing with a link to it.
    msg = build_message(results)
    url = os.environ.get("DASHBOARD_URL", "").strip()
    if url:
        msg += (f"\n\n🖥 <b>Trade Command Center (live):</b> "
                f"<a href=\"{url}\">open dashboard</a> — MTF matrix, strategies, "
                f"conviction, fundamentals and tagged news.")
    if os.environ.get("DRY_RUN"):
        print("\n" + "=" * 60 + "\n" + msg)
    else:
        send(msg)
        print(f"\nPosted briefing covering {total} instruments.")


if __name__ == "__main__":
    main()
