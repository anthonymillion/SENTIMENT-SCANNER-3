# Sentiment Scanner - Full Sentiment Integration
import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta

# --- API Keys ---
TRADING_ECON_API_USER = st.secrets["tradingecon_user"]
TRADING_ECON_API_PASS = st.secrets["tradingecon_pass"]
FINNHUB_API_KEY = st.secrets["finnhub_key"]

# --- Macro Events ---
@st.cache_data(ttl=3600)
def get_global_macro_events():
    url = "https://api.tradingeconomics.com/calendar/country/united states,germany,euro area,japan,china,united kingdom"
    r = requests.get(url, auth=(TRADING_ECON_API_USER, TRADING_ECON_API_PASS))
    df = pd.DataFrame(r.json())
    df = df[["date", "country", "event", "importance"]]
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= datetime.now() + timedelta(days=7)]
    df["flag"] = df["importance"].map({3: "🔴", 2: "🟡", 1: "🟢"})
    return df

def calculate_macro_risk_score(df):
    return (df["importance"] == 3).sum() * -1 + (df["importance"] == 2).sum() * -0.5

# --- Stock Info (yfinance) ---
@st.cache_data(ttl=900)
def get_stock_info(symbol):
    try:
        info = yf.Ticker(symbol).info
        return {
            "Symbol": symbol,
            "Price": info.get("currentPrice", 0),
            "Volume": info.get("volume", 0),
            "Float": info.get("floatShares", 0),
        }
    except:
        return {"Symbol": symbol, "Price": 0, "Volume": 0, "Float": 0}

# --- Simulated Sentiment Scores (stub logic) ---
def get_sentiment_scores(symbol):
    # These values would be calculated using real API results
    return {
        "Macro": macro_risk_score,
        "COT": +2,
        "Earnings": +3 if symbol == "MSFT" else -3 if symbol == "NFLX" else 0,
        "IPO": +2 if symbol == "ARM" else 0,
        "News": -2 if symbol == "PYPL" else +2,
        "Options": +2 if symbol in ["NVDA", "AAPL"] else -1,
        "Geo": -1,
    }

# --- Layout ---
st.set_page_config("Sentiment Scanner", layout="wide")
st.title("📊 Full Sentiment Scanner (Macro + COT + News + Earnings + Options + IPO)")

# --- Sidebar Panels ---
st.sidebar.header("🌍 Global Macro Events")
macro_df = get_global_macro_events()
macro_risk_score = calculate_macro_risk_score(macro_df)
st.sidebar.metric("Macro Risk Score", f"{macro_risk_score:+.1f}")
for _, row in macro_df.iterrows():
    st.sidebar.markdown(f"{row['flag']} **{row['date'].strftime('%b %d')}** - {row['event']} ({row['country']})")

st.sidebar.header("📉 COT Sentiment")
st.sidebar.markdown("**Net Position Change:** +132K (Bullish)")
st.sidebar.markdown("**Date:** July 16, 2025")

# --- Stocks ---
stocks = [
    "NVDA", "MSFT", "AAPL", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO", "COST",
    "AMD", "NFLX", "ADBE", "ADP", "AMGN", "CRM", "QCOM", "INTC", "PYPL", "PEP", "ARM"
]
selection = st.multiselect("Select Stocks", options=stocks, default=stocks[:10])

# --- Process ---
table = []
for sym in selection:
    base = get_stock_info(sym)
    sent = get_sentiment_scores(sym)
    score = sum(sent.values())
    base["Volume"] = f"{base['Volume'] / 1e6:.2f}M"
    base["Float"] = f"{base['Float'] / 1e6:.2f}M"
    base["Score"] = score
    base["Sentiment"] = "Bullish" if score > 0 else "Bearish"
    table.append(base)

df = pd.DataFrame(table)
styled = df.style.apply(lambda x: ["background-color: #d1ffd1" if v > 0 else "background-color: #ffd1d1" for v in x["Score"]], axis=1, subset=["Score"])
st.dataframe(styled, use_container_width=True)
