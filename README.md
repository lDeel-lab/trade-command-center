# Telegram Market Bot + Trade Command Center

**Phase 2 layout:** `dashboard.html` is the Trade Command Center (deployed to GitHub Pages as the site's index). The **data workflow** (`.github/workflows/data.yml`) runs every 15 minutes and rebuilds: per-tab market candles (`build_markets.py` — indices, FX, commodities, US/UK/Europe/India/Japan/China·HK), tagged global news (`build_news.py` — domain › sector › region hierarchy + per-instrument matching), and daily equity fundamentals (`build_fundamentals.py` — P/E, forward P/E, EPS, growth, margins, targets, scored −3…+3 into conviction). Crypto stays fully live in the browser via Bybit; the Telegram daily briefing below is unchanged. Setup: same as before **plus** Settings → Pages → Source: GitHub Actions, then run "Dashboard data refresh" once from the Actions tab. India tab is analysis-only (IG doesn't offer Indian shares as spread bets).

Two automated jobs, both free on GitHub Actions:

| Job | Schedule | What it posts |
|---|---|---|
| **Daily market briefing** | 06:00 UTC every day (weekends: crypto only) | Buy/sell/neutral bias with Entry, SL, TP1/TP2/TP3 for ~60 instruments: US/EU/UK/Asia indices, US + UK/EU large caps, crypto, commodities, FX — **plus an interactive web dashboard** (see below) linked at the bottom of the post |
| **Hourly news digest** | Every hour at :12 | New headlines from CNBC, MarketWatch, Yahoo Finance, BBC Business, Investing.com, ForexLive, CoinDesk, Cointelegraph — de-duplicated, only what's new since last run |

## The interactive dashboard

Each morning the briefing job also generates `site/index.html` — a self-contained interactive dashboard published to **GitHub Pages**:

- It opens on the **Trade Board**: today's buy and sell setups ranked strongest-first, with every price on the row — market entry, pullback entry (20-day EMA), stop loss, and TP1/TP2/TP3 with % distances. Tap a row for the full detail.
- An **All instruments** tab with filter buttons for every market group (US indices, Europe/UK, Asia, US stocks, UK/EU stocks, crypto, commodities, FX) plus Buy/Sell/Neutral filters and instant search.
- Click any instrument for a 60-day chart (close + EMA20 + EMA50 with crosshair tooltip), the full trade plan (entries / SL / TP1 / TP2 / TP3 / support / resistance), the 6-point score breakdown, and a plain-English explanation of the setup.
- A **News** tab with the latest headlines from all the RSS sources.
- Light/dark theme, works on mobile.

**Enable it once:** repo → *Settings → Pages → Source: GitHub Actions*. That's all — the daily workflow deploys it automatically, and the Telegram post links to `https://<your-username>.github.io/<repo-name>/`.

> **Note:** on a free GitHub account, Pages only works on **public** repos. The code contains no secrets (the token lives in Actions secrets), so public is safe — but if you'd rather stay private, set a repository *variable* `SEND_HTML` to `1` (Settings → Secrets and variables → Actions → Variables) and the bot will attach the dashboard HTML file to the Telegram post instead; members download it and open it in a browser.

Signals are systematic technical levels (EMA 20/50/200, RSI 14, MACD, ATR 14 — stop is 1.5×ATR, TP1/TP2 are 1R/2R). **Not financial advice**; every post carries a disclaimer.

## Setup (10 minutes)

### 1. Telegram side

1. You already have a bot token from **@BotFather**. Keep it secret — if it was ever shared publicly, send `/revoke` to BotFather and use the new one.
2. Open your channel → *Administrators* → *Add admin* → search your bot's username → add it (only "Post messages" permission needed).
3. Get the channel's chat ID:
   - **Public channel**: the ID is simply `@yourchannelname`.
   - **Private channel**: post any message in the channel, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser (replace `<TOKEN>`; if empty, forward a channel post to the bot first). Look for `"chat":{"id":-100xxxxxxxxxx}` — that negative number is your chat ID.

### 2. GitHub side

1. Create a **private** repository (e.g. `telegram-market-bot`) at github.com.
2. Upload all files from this folder, keeping the structure — the `.github/workflows/` folder is what makes the schedules run. Easiest: on the repo page, *Add file → Upload files*, drag the whole folder contents in. (If the `.github` folder won't drag in the browser, create the two workflow files manually via *Add file → Create new file* using paths `.github/workflows/daily-signals.yml` etc.)
3. Repo → *Settings → Secrets and variables → Actions → New repository secret*, add two secrets:
   - `TELEGRAM_BOT_TOKEN` — your BotFather token
   - `TELEGRAM_CHAT_ID` — `@yourchannelname` or the `-100…` number
4. Repo → *Actions* tab → enable workflows if prompted.

### 3. Test immediately

*Actions* tab → **Daily market briefing** → *Run workflow*. Within ~2–3 minutes the briefing should appear in your channel. Do the same for **Hourly news digest**.

## Customising

- **Instruments**: edit `watchlist.py` — add/remove any Yahoo Finance ticker; sections and ordering are just the dict structure.
- **Timing**: edit the `cron:` lines in `.github/workflows/*.yml` (times are UTC; 06:00 UTC = 07:00 UK in summer, 06:00 UK in winter).
- **News sources**: edit the `FEEDS` dict in `news.py` — any RSS feed works. To add real X/Twitter later, a `fetch_tweets()` source can be added to the same digest once you have an X API key.
- **Signal rules**: `signals.py` — thresholds (`score >= 4`), stop width (`SL_ATR`), and R-multiples (`TP1_R`, `TP2_R`) are constants at the top.
- **Local dry run**: `DRY_RUN=1 python signals.py` prints the message instead of posting.

## Notes

- GitHub Actions cron can start a few minutes late at busy times — normal.
- If a data source hiccups on one instrument, it's skipped and the rest post fine; if *nothing* fetches, the job fails without posting garbage.
- Scheduled workflows on free accounts pause after ~60 days without a repo commit — any tiny commit (or the news job's own state commits) keeps them alive.
