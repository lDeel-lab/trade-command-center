"""Watchlist configuration — every instrument the daily briefing covers.

Symbols are Yahoo Finance tickers. Each entry: (yahoo_symbol, display_name).
Edit freely — add or remove instruments; the briefing adapts automatically.
Sections are posted in this order.
"""

WATCHLIST = {
    "🇺🇸 US INDICES": [
        ("^GSPC", "S&P 500"),
        ("^NDX", "Nasdaq 100"),
        ("^DJI", "Dow Jones"),
        ("^RUT", "Russell 2000"),
    ],
    "🇪🇺 EUROPE & 🇬🇧 UK INDICES": [
        ("^FTSE", "FTSE 100"),
        ("^GDAXI", "DAX 40"),
        ("^FCHI", "CAC 40"),
        ("^STOXX50E", "Euro Stoxx 50"),
        ("^IBEX", "IBEX 35"),
        ("FTSEMIB.MI", "FTSE MIB"),
    ],
    "🌏 ASIA & GLOBAL INDICES": [
        ("^N225", "Nikkei 225"),
        ("^HSI", "Hang Seng"),
        ("^NSEI", "Nifty 50"),
        ("^BSESN", "Sensex"),
        ("^AXJO", "ASX 200"),
        ("^GSPTSE", "TSX Composite"),
    ],
    "🏦 US LARGE CAPS": [
        ("AAPL", "Apple"),
        ("MSFT", "Microsoft"),
        ("NVDA", "Nvidia"),
        ("AMZN", "Amazon"),
        ("GOOGL", "Alphabet"),
        ("META", "Meta"),
        ("TSLA", "Tesla"),
        ("AVGO", "Broadcom"),
        ("JPM", "JPMorgan"),
        ("BRK-B", "Berkshire B"),
    ],
    "🇬🇧🇪🇺 UK & EUROPE LARGE CAPS": [
        ("SHEL.L", "Shell"),
        ("AZN.L", "AstraZeneca"),
        ("HSBA.L", "HSBC"),
        ("BP.L", "BP"),
        ("ULVR.L", "Unilever"),
        ("ASML.AS", "ASML"),
        ("SAP.DE", "SAP"),
        ("MC.PA", "LVMH"),
        ("NESN.SW", "Nestlé"),
        ("NOVO-B.CO", "Novo Nordisk"),
    ],
    "₿ CRYPTO": [
        ("BTC-USD", "Bitcoin"),
        ("ETH-USD", "Ethereum"),
        ("SOL-USD", "Solana"),
        ("BNB-USD", "BNB"),
        ("XRP-USD", "XRP"),
        ("ADA-USD", "Cardano"),
        ("DOGE-USD", "Dogecoin"),
        ("AVAX-USD", "Avalanche"),
        ("LINK-USD", "Chainlink"),
        ("DOT-USD", "Polkadot"),
    ],
    "🛢️ COMMODITIES": [
        ("GC=F", "Gold"),
        ("SI=F", "Silver"),
        ("PL=F", "Platinum"),
        ("CL=F", "WTI Crude"),
        ("BZ=F", "Brent Crude"),
        ("NG=F", "Nat Gas"),
        ("HG=F", "Copper"),
        ("ZW=F", "Wheat"),
        ("ZC=F", "Corn"),
    ],
    "💱 FX & DOLLAR": [
        ("DX-Y.NYB", "DXY Index"),
        ("EURUSD=X", "EUR/USD"),
        ("GBPUSD=X", "GBP/USD"),
        ("USDJPY=X", "USD/JPY"),
        ("AUDUSD=X", "AUD/USD"),
        ("USDCHF=X", "USD/CHF"),
    ],
}

# Sections that trade 24/7 — the only ones posted on weekends.
WEEKEND_SECTIONS = {"₿ CRYPTO"}
