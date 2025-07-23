import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
import time

# === API Keys ===
FINNHUB_API_KEY = "d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohv0d1uv2rhr01qujmdeohvg"
TRADING_ECON_USER = "c88d1d122399451"
TRADING_ECON_KEY = "rdog9czpshn7zb9"

# === Stock List ===
stock_list = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST", "AMD", "NFLX",
    "ABNB", "ADBE", "ADI", "ADP", "ADSK", "AEP", "AMAT", "AMGN", "APP", "ANSS", "ARM", "ASML", "AXON",
    "AZN", "BIIB", "BKNG", "BKR", "CCEP", "CDNS", "CDW", "CEG", "CHTR", "CMCSA", "CPRT", "CSGP", "CSCO",
    "CSX", "CTAS", "CTSH", "CRWD", "DASH", "DDOG", "DXCM", "EA", "EXC", "FAST", "FANG", "FTNT", "GEHC",
    "GILD", "GFS", "HON", "IDXX", "INTC", "INTU", "ISRG", "KDP", "KHC", "KLAC", "LIN", "LRCX", "LULU",
    "MAR", "MCHP", "MDLZ", "MELI", "MNST", "MRVL", "MSTR", "MU", "NXPI", "ODFL", "ON", "ORLY", "PANW",
    "PAYX", "PYPL", "PDD", "PEP", "PLTR", "QCOM", "REGN", "ROP", "ROST", "SHOP", "SBUX", "SNPS", "TTWO",
    "TMUS", "TXN", "TTD", "VRSK", "VRTX", "WBD", "WDAY", "XEL", "ZS"
]

macro_symbols = {
    "DXY": "DXY", "USDJPY": "USDJPY=X", "XAUUSD": "XAUUSD=X", "EURUSD": "EURUSD=X",
    "USOIL": "CL=F", "USTECH100": "^NDX", "S&P500": "^GSPC", "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD", "RUSSEL2000": "^RUT", "NIKKEI": "^N225", "SILVER": "SI=F",
    "QQQ": "QQQ", "NATGAS": "NG=F", "COPPER": "HG=F", "BRENT": "BZ=F", "VIX": "^VIX", "BONDYIELD": "^TNX"
}

# === Streamlit Setup ===
st.set_page_config(layout="wide")
st.title("Sentiment Scanner")

REFRESH_INTERVAL = 60  # in seconds
st_autorefresh = st.experimental_rerun if int(time.time()) % REFRESH_INTERVAL == 0 else lambda: None

with st.sidebar:
    st.title("Settings")
    timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "1d"])
    st.info("Auto-refresh every 60 seconds")

# === Macro Risk Score ===
def get_macro_risk_score():
    try:
        url = f"https://api.tradingeconomics.com/calendar/country/united states?c={TRADING_ECON_USER}:{TRADING_ECON_KEY}"
        res = requests.get(url).json()
        red = sum(1 for e in res if e.get("importance") == 3)
        yellow = sum(1 for e in res if e.get("importance") == 2)
        return red + 0.5 * yellow
    except:
        return 0

# === Combined Score ===
def get_combined_score(symbol):
    score = 0
    try:
        news = requests.get(f"https://finnhub.io/api/v1/news-sentiment?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        if news.get("companyNewsScore", 0) > 0.2: score += 1
        elif news.get("companyNewsScore", 0) < -0.2: score -= 1
        if news.get("sectorAverageBullishPercent", 0) > 0.5: score += 1
    except: pass

    try:
        earnings = requests.get(f"https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&token={FINNHUB_API_KEY}").json()
        for e in earnings.get("earningsCalendar", []):
            if float(e.get("epsActual", 0)) > float(e.get("epsEstimate", 0)): score += 1
            elif float(e.get("epsActual", 0)) < float(e.get("epsEstimate", 0)): score -= 1
    except: pass

    try:
        start = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")
        end = datetime.today().strftime("%Y-%m-%d")
        ipo = requests.get(f"https://finnhub.io/api/v1/calendar/ipo?from={start}&to={end}&token={FINNHUB_API_KEY}").json()
        for i in ipo.get("ipoCalendar", []):
            if i.get("symbol") == symbol: score += 1
    except: pass

    if get_macro_risk_score() > 6: score -= 1
    return score

# === Symbol Data Processor ===
def process_symbol(symbol, label=None, is_macro=False):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval=timeframe)
        if hist.empty: raise ValueError("No history")

        price = hist["Close"][-1]
        volume = hist["Volume"][-1]
        info = ticker.fast_info

        float_shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")

        score = get_combined_score(symbol) if not is_macro else 0
        trend = "UPTREND" if score > 0 else "DOWNTREND" if score < 0 else "NEUTRAL"
        sentiment = "🟢 Bullish" if score > 0 else "🔴 Bearish" if score < 0 else "⚪ Neutral"

        if score > 1: driver = "News"
        elif score == 1: driver = "Earnings"
        else: driver = "Options"

        return {
            "Symbol": label or symbol,
            "Price": f"${price:.2f}",
            "Volume": f"{volume/1e6:.2f}M",
            "Float": f"{float_shares/1e6:.2f}M" if float_shares else "—",
            "CAP": f"${market_cap/1e9:.2f}B" if market_cap else "N/A",
            "Score": score,
            "Trend": trend,
            "Sentiment": sentiment,
            "Driver": driver
        }
    except:
        return {
            "Symbol": label or symbol,
            "Price": "N/A", "Volume": "N/A", "Float": "N/A",
            "CAP": "N/A", "Score": 0, "Trend": "NEUTRAL", "Sentiment": "⚪ Neutral", "Driver": "-"
        }

# === Cell Styling ===
def style_df(df):
    return (df.style
            .applymap(lambda val: "background-color: #6c757d; color: white; font-weight: bold; text-align: center;", subset=["Symbol"])
            .applymap(lambda val: "background-color: #d4edda; color: #155724; font-weight: bold; text-align: center;", subset=["Price"])
            .applymap(lambda val: "background-color: #cce5ff; color: #004085; font-weight: bold; text-align: center;", subset=["Volume"])
            .applymap(lambda val: "background-color: #6495ed; color: white; font-weight: bold; text-align: center;", subset=["Score"])
            .applymap(lambda val: f"background-color: {{'UPTREND': '#28a745', 'DOWNTREND': '#dc3545', 'NEUTRAL': '#6c757d'}.get(val, '#6c757d')}; color: white; font-weight: bold; text-align: center;", subset=["Trend"])
            .applymap(lambda val: f"background-color: {{'🟢 Bullish': '#28a745', '🔴 Bearish': '#dc3545', '⚪ Neutral': '#6c757d'}.get(val, '#6c757d')}; color: white; font-weight: bold; text-align: center;", subset=["Sentiment"])
            .applymap(lambda val: f"background-color: {{'News': '#17a2b8', 'Earnings': '#ffc107', 'Options': '#6f42c1', '-': '#6c757d'}.get(val, '#6c757d')}; color: white; font-weight: bold; text-align: center;", subset=["Driver"])
            .format({"Score": lambda x: f"+{x}" if x > 0 else str(x)})
            .set_properties(**{'text-align': 'center'})
            .set_table_styles([
                {'selector': 'th', 'props': [('text-align', 'center'), ('background-color', '#222'), ('color', '#ddd'), ('border', '2px solid #444')]},
                {'selector': 'td', 'props': [('border', '1px solid #444'), ('padding', '6px 10px'), ('font-size', '14px')]}
            ])
           )

# === Build DataFrames ===
stock_data = [process_symbol(sym) for sym in stock_list]
stock_df = pd.DataFrame(stock_data).sort_values("Score", ascending=False)

macro_data = [process_symbol(tick, name, is_macro=True) for name, tick in macro_symbols.items()]
macro_df = pd.DataFrame(macro_data).sort_values("Score", ascending=False)

# === Layout Display ===
st.markdown("### NASDAQ-100 Stocks")
st.dataframe(style_df(stock_df), use_container_width=True)

st.markdown("### Global Market Symbols")
st.dataframe(style_df(macro_df), use_container_width=True)

# Trigger auto-refresh manually
st_autor
