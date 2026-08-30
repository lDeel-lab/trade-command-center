"""The full instrument universe with hierarchical tags.

Every instrument: (yahoo_symbol, display_name, cls, region, sector, ig, tv, aliases)
  cls    : index | fx | commodity | stock    (crypto lives client-side via Bybit)
  region : US | UK | Europe | India | Japan | ChinaHK | Global
  sector : GICS-ish sector for stocks; group for commodities; "" otherwise
  ig     : True if tradeable as an IG spread bet (Indian shares are not)
  tv     : TradingView symbol for the embedded live chart
  aliases: extra lowercase strings for news matching (name is matched automatically)

Grouped into FILES — one JSON per dashboard tab.
"""

I = lambda y, n, tv, al=(): (y, n, "index", "Global", "", True, tv, al)
F = lambda y, n, tv, al=(): (y, n, "fx", "Global", "", True, tv, al)
C = lambda y, n, g, tv, al=(): (y, n, "commodity", "Global", g, True, tv, al)
S = lambda y, n, r, s, tv, ig=True, al=(): (y, n, "stock", r, s, ig, tv, al)

FILES = {
"indices": [
  I("^GSPC","S&P 500","SP:SPX",("spx","s&p")), I("^NDX","Nasdaq 100","NASDAQ:NDX",("nasdaq",)),
  I("^DJI","Dow Jones","DJ:DJI",("dow",)), I("^RUT","Russell 2000","TVC:RUT",("russell",)),
  I("^FTSE","FTSE 100","SPREADEX:FTSE",("ftse",)), I("^GDAXI","DAX 40","XETR:DAX",("dax",)),
  I("^FCHI","CAC 40","TVC:CAC40",("cac",)), I("^STOXX50E","Euro Stoxx 50","TVC:SX5E",("stoxx",)),
  I("^IBEX","IBEX 35","BME:IBC",("ibex",)), I("FTSEMIB.MI","FTSE MIB","MIL:FTSEMIB",("mib",)),
  I("^SSMI","SMI 20","SIX:SMI",("smi","swiss market")),
  I("^N225","Nikkei 225","TVC:NI225",("nikkei",)), I("^HSI","Hang Seng","TVC:HSI",("hang seng",)),
  I("^NSEI","Nifty 50","NSE:NIFTY",("nifty",)), I("^BSESN","Sensex","BSE:SENSEX",("sensex",)),
  I("^AXJO","ASX 200","ASX:XJO",("asx",)), I("^GSPTSE","TSX Composite","TSX:TSX",("tsx",)),
  I("^KS11","KOSPI","KRX:KOSPI",("kospi",)),
],
"fx": [
  F("DX-Y.NYB","DXY Dollar Index","TVC:DXY",("dxy","dollar index")),
  F("EURUSD=X","EUR/USD","FX:EURUSD",("euro",)), F("GBPUSD=X","GBP/USD","FX:GBPUSD",("sterling","cable","pound")),
  F("USDJPY=X","USD/JPY","FX:USDJPY",("yen",)), F("AUDUSD=X","AUD/USD","FX:AUDUSD",("aussie",)),
  F("NZDUSD=X","NZD/USD","FX:NZDUSD",("kiwi",)), F("USDCAD=X","USD/CAD","FX:USDCAD",()),
  F("USDCHF=X","USD/CHF","FX:USDCHF",("franc",)), F("EURGBP=X","EUR/GBP","FX:EURGBP",()),
  F("EURJPY=X","EUR/JPY","FX:EURJPY",()), F("GBPJPY=X","GBP/JPY","FX:GBPJPY",()),
],
"commodities": [
  C("GC=F","Gold","metals","TVC:GOLD",("bullion",)), C("SI=F","Silver","metals","TVC:SILVER"),
  C("PL=F","Platinum","metals","TVC:PLATINUM"), C("HG=F","Copper","metals","COMEX:HG1!"),
  C("CL=F","WTI Crude","energy","TVC:USOIL",("crude","wti")), C("BZ=F","Brent Crude","energy","TVC:UKOIL",("brent",)),
  C("NG=F","Nat Gas","energy","NYMEX:NG1!",("natural gas",)),
  C("ZW=F","Wheat","agriculture","CBOT:ZW1!"), C("ZC=F","Corn","agriculture","CBOT:ZC1!"),
  C("ZS=F","Soybeans","agriculture","CBOT:ZS1!",("soybean",)),
  C("KC=F","Coffee","agriculture","ICEUS:KC1!"), C("SB=F","Sugar","agriculture","ICEUS:SB1!"),
  C("CC=F","Cocoa","agriculture","ICEUS:CC1!"), C("CT=F","Cotton","agriculture","ICEUS:CT1!"),
],
"us": [
  S("AAPL","Apple","US","Technology","NASDAQ:AAPL"), S("MSFT","Microsoft","US","Technology","NASDAQ:MSFT"),
  S("NVDA","Nvidia","US","Technology","NASDAQ:NVDA"), S("GOOGL","Alphabet","US","Technology","NASDAQ:GOOGL",True,("google",)),
  S("AMZN","Amazon","US","Consumer","NASDAQ:AMZN"), S("META","Meta","US","Technology","NASDAQ:META",True,("facebook","instagram")),
  S("TSLA","Tesla","US","Autos","NASDAQ:TSLA"), S("AVGO","Broadcom","US","Technology","NASDAQ:AVGO"),
  S("AMD","AMD","US","Technology","NASDAQ:AMD"), S("INTC","Intel","US","Technology","NASDAQ:INTC"),
  S("CRM","Salesforce","US","Technology","NYSE:CRM"), S("ORCL","Oracle","US","Technology","NYSE:ORCL"),
  S("NFLX","Netflix","US","Consumer","NASDAQ:NFLX"), S("PLTR","Palantir","US","Technology","NASDAQ:PLTR"),
  S("COIN","Coinbase","US","Financials","NASDAQ:COIN"), S("JPM","JPMorgan","US","Financials","NYSE:JPM"),
  S("BAC","Bank of America","US","Financials","NYSE:BAC"), S("V","Visa","US","Financials","NYSE:V"),
  S("BRK-B","Berkshire B","US","Financials","NYSE:BRK.B",True,("berkshire","buffett")),
  S("UNH","UnitedHealth","US","Healthcare","NYSE:UNH"), S("JNJ","Johnson & Johnson","US","Healthcare","NYSE:JNJ"),
  S("LLY","Eli Lilly","US","Healthcare","NYSE:LLY"), S("XOM","Exxon Mobil","US","Energy","NYSE:XOM",True,("exxon",)),
  S("CVX","Chevron","US","Energy","NYSE:CVX"), S("WMT","Walmart","US","Consumer","NYSE:WMT"),
  S("KO","Coca-Cola","US","Consumer","NYSE:KO"), S("PG","Procter & Gamble","US","Consumer","NYSE:PG"),
  S("HD","Home Depot","US","Consumer","NYSE:HD"), S("MCD","McDonald's","US","Consumer","NYSE:MCD"),
  S("CAT","Caterpillar","US","Industrials","NYSE:CAT"), S("BA","Boeing","US","Industrials","NYSE:BA"),
  S("GE","GE Aerospace","US","Industrials","NYSE:GE"),
],
"uk": [
  S("SHEL.L","Shell","UK","Energy","LSE:SHEL"), S("BP.L","BP","UK","Energy","LSE:BP"),
  S("AZN.L","AstraZeneca","UK","Healthcare","LSE:AZN"), S("GSK.L","GSK","UK","Healthcare","LSE:GSK",True,("glaxo",)),
  S("HSBA.L","HSBC","UK","Financials","LSE:HSBA"), S("BARC.L","Barclays","UK","Financials","LSE:BARC"),
  S("LLOY.L","Lloyds","UK","Financials","LSE:LLOY"), S("ULVR.L","Unilever","UK","Consumer","LSE:ULVR"),
  S("TSCO.L","Tesco","UK","Consumer","LSE:TSCO"), S("BATS.L","BAT","UK","Consumer","LSE:BATS",True,("british american tobacco",)),
  S("RIO.L","Rio Tinto","UK","Materials","LSE:RIO"), S("GLEN.L","Glencore","UK","Materials","LSE:GLEN"),
  S("AAL.L","Anglo American","UK","Materials","LSE:AAL"), S("VOD.L","Vodafone","UK","Telecom","LSE:VOD"),
  S("BT-A.L","BT Group","UK","Telecom","LSE:BT.A"), S("RR.L","Rolls-Royce","UK","Industrials","LSE:RR",True,("rolls royce",)),
  S("REL.L","RELX","UK","Industrials","LSE:REL"),
],
"europe": [
  S("ASML.AS","ASML","Europe","Technology","EURONEXT:ASML"), S("SAP.DE","SAP","Europe","Technology","XETR:SAP"),
  S("IFX.DE","Infineon","Europe","Technology","XETR:IFX"), S("MC.PA","LVMH","Europe","Consumer","EURONEXT:MC"),
  S("OR.PA","L'Oréal","Europe","Consumer","EURONEXT:OR",True,("loreal",)),
  S("NESN.SW","Nestlé","Europe","Consumer","SIX:NESN",True,("nestle",)),
  S("TTE.PA","TotalEnergies","Europe","Energy","EURONEXT:TTE",True,("total",)),
  S("SIE.DE","Siemens","Europe","Industrials","XETR:SIE"), S("AIR.PA","Airbus","Europe","Industrials","EURONEXT:AIR"),
  S("ALV.DE","Allianz","Europe","Financials","XETR:ALV"), S("BNP.PA","BNP Paribas","Europe","Financials","EURONEXT:BNP"),
  S("SAN.PA","Sanofi","Europe","Healthcare","EURONEXT:SAN"), S("NOVN.SW","Novartis","Europe","Healthcare","SIX:NOVN"),
  S("ROG.SW","Roche","Europe","Healthcare","SIX:ROG"), S("NOVO-B.CO","Novo Nordisk","Europe","Healthcare","OMXCOP:NOVO_B",True,("novo",)),
  S("ENEL.MI","Enel","Europe","Utilities","MIL:ENEL"), S("ISP.MI","Intesa Sanpaolo","Europe","Financials","MIL:ISP",True,("intesa",)),
],
"india": [   # analysis-only: IG does not offer Indian shares as spread bets
  S("RELIANCE.NS","Reliance Industries","India","Energy","NSE:RELIANCE",False,("reliance",)),
  S("TCS.NS","TCS","India","Technology","NSE:TCS",False,("tata consultancy",)),
  S("INFY.NS","Infosys","India","Technology","NSE:INFY",False),
  S("HDFCBANK.NS","HDFC Bank","India","Financials","NSE:HDFCBANK",False),
  S("ICICIBANK.NS","ICICI Bank","India","Financials","NSE:ICICIBANK",False),
  S("SBIN.NS","State Bank of India","India","Financials","NSE:SBIN",False,("sbi",)),
  S("BHARTIARTL.NS","Bharti Airtel","India","Telecom","NSE:BHARTIARTL",False,("airtel",)),
  S("ITC.NS","ITC","India","Consumer","NSE:ITC",False),
  S("HINDUNILVR.NS","Hindustan Unilever","India","Consumer","NSE:HINDUNILVR",False),
  S("LT.NS","Larsen & Toubro","India","Industrials","NSE:LT",False,("larsen",)),
  S("TATAMOTORS.NS","Tata Motors","India","Autos","NSE:TATAMOTORS",False),
  S("ADANIENT.NS","Adani Enterprises","India","Industrials","NSE:ADANIENT",False,("adani",)),
],
"japan": [
  S("7203.T","Toyota","Japan","Autos","TSE:7203"), S("6758.T","Sony","Japan","Technology","TSE:6758"),
  S("9984.T","SoftBank Group","Japan","Technology","TSE:9984",True,("softbank",)),
  S("8306.T","MUFG","Japan","Financials","TSE:8306",True,("mitsubishi ufj",)),
  S("6501.T","Hitachi","Japan","Industrials","TSE:6501"), S("7974.T","Nintendo","Japan","Consumer","TSE:7974"),
  S("9983.T","Fast Retailing","Japan","Consumer","TSE:9983",True,("uniqlo",)),
  S("8035.T","Tokyo Electron","Japan","Technology","TSE:8035"),
  S("6861.T","Keyence","Japan","Technology","TSE:6861"), S("6098.T","Recruit Holdings","Japan","Industrials","TSE:6098"),
],
"chinahk": [
  S("0700.HK","Tencent","ChinaHK","Technology","HKEX:700"), S("9988.HK","Alibaba","ChinaHK","Consumer","HKEX:9988",True,("baba",)),
  S("3690.HK","Meituan","ChinaHK","Consumer","HKEX:3690"), S("1810.HK","Xiaomi","ChinaHK","Technology","HKEX:1810"),
  S("9618.HK","JD.com","ChinaHK","Consumer","HKEX:9618",True,("jd",)),
  S("1211.HK","BYD","ChinaHK","Autos","HKEX:1211"), S("9868.HK","XPeng","ChinaHK","Autos","HKEX:9868"),
  S("2318.HK","Ping An","ChinaHK","Financials","HKEX:2318"), S("1299.HK","AIA","ChinaHK","Financials","HKEX:1299"),
  S("0941.HK","China Mobile","ChinaHK","Telecom","HKEX:941"),
],
"emerging": [
  # Liquidity-first emerging markets: every entry is a deeply-traded US listing/ADR
  # (NYSE/NASDAQ), reachable through IG share dealing, IBKR and mostly Revolut —
  # local-only exchanges (Johannesburg, São Paulo, El Salvador has none) are
  # deliberately reached through their liquid ADRs instead.
  # Latin America
  S("MELI","MercadoLibre","Emerging","Consumer","NASDAQ:MELI",True,("mercado libre","mercadolibre")),
  S("NU","Nu Holdings","Emerging","Financials","NYSE:NU",True,("nubank",)),
  S("VALE","Vale","Emerging","Materials","NYSE:VALE",True,("iron ore miner",)),
  S("PBR","Petrobras","Emerging","Energy","NYSE:PBR",True,("petrobras",)),
  S("ITUB","Itaú Unibanco","Emerging","Financials","NYSE:ITUB",True,("itau",)),
  S("ABEV","Ambev","Emerging","Consumer","NYSE:ABEV",True,("ambev",)),
  S("AMX","América Móvil","Emerging","Telecom","NYSE:AMX",True,("america movil",)),
  S("FMX","FEMSA","Emerging","Consumer","NYSE:FMX",True,("femsa",)),
  S("CX","Cemex","Emerging","Materials","NYSE:CX",True,("cemex",)),
  S("EC","Ecopetrol","Emerging","Energy","NYSE:EC",True,("ecopetrol",)),
  S("BAP","Credicorp","Emerging","Financials","NYSE:BAP",True,("credicorp",)),
  S("SCCO","Southern Copper","Emerging","Materials","NYSE:SCCO",True,("southern copper",)),
  S("SQM","SQM (Lithium)","Emerging","Materials","NYSE:SQM",True,("sqm","lithium chile")),
  S("YPF","YPF","Emerging","Energy","NYSE:YPF",True,("ypf",)),
  S("GGAL","Grupo Galicia","Emerging","Financials","NASDAQ:GGAL",True,("galicia",)),
  # Africa
  S("AU","AngloGold Ashanti","Emerging","Materials","NYSE:AU",True,("anglogold",)),
  S("GFI","Gold Fields","Emerging","Materials","NYSE:GFI",True,("gold fields",)),
  S("SBSW","Sibanye-Stillwater","Emerging","Materials","NYSE:SBSW",True,("sibanye",)),
  S("HMY","Harmony Gold","Emerging","Materials","NYSE:HMY",True,("harmony gold",)),
  # Asia & beyond
  S("SE","Sea Limited","Emerging","Technology","NYSE:SE",True,("shopee","garena")),
  S("GRAB","Grab Holdings","Emerging","Technology","NASDAQ:GRAB",True,("grab",)),
  S("TLK","Telkom Indonesia","Emerging","Telecom","NYSE:TLK",True,("telkom indonesia",)),
  S("KSPI","Kaspi.kz","Emerging","Financials","NASDAQ:KSPI",True,("kaspi",)),
  S("TKC","Turkcell","Emerging","Telecom","NYSE:TKC",True,("turkcell",)),
],
}

# static descriptions for non-stock instruments (stocks get Yahoo's business summary)
STATIC_DESC = {
  "index": "Equity index — a capitalisation-weighted basket representing its market. "
    "Fundamentals to watch: aggregate valuation vs history, earnings season breadth, "
    "rate expectations for its region, and currency effects on exporters.",
  "fx": "Currency pair — driven by interest-rate differentials, central-bank policy paths, "
    "growth and inflation surprises, and risk appetite. The economic calendar IS the fundamentals.",
  "commodity": "Physical commodity future — driven by supply (production, OPEC/weather/strikes), "
    "demand cycles, inventories, the dollar, and positioning (COT). No earnings — the curve and "
    "stock levels are the balance sheet.",
}

def all_instruments():
    out = []
    for fkey, rows in FILES.items():
        for (y, n, cls, region, sector, ig, tv, al) in rows:
            out.append({"id": y, "name": n, "cls": cls, "region": region,
                        "sector": sector, "ig": ig, "tv": tv, "file": fkey,
                        "aliases": list(al)})
    return out

if __name__ == "__main__":
    insts = all_instruments()
    print(f"{len(insts)} instruments in {len(FILES)} files")
    for f in FILES: print(" ", f, len(FILES[f]))
