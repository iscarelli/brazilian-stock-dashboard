import os
import tempfile

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Diretório temporário por processo — evita "database is locked" do cache SQLite do yfinance
yf.set_tz_cache_location(os.path.join(tempfile.gettempdir(), f"yf_cache_{os.getpid()}"))

TICKERS = ["PETR4.SA", "ITUB4.SA", "VALE3.SA"]
TICKER_LABELS = {
    "PETR4.SA": "PETR4",
    "ITUB4.SA": "ITUB4",
    "VALE3.SA": "VALE3",
}
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"


@st.cache_data(ttl=3600)
def fetch_stock_data() -> pd.DataFrame:
    """Download OHLCV data for all tickers from yfinance.
    Retries up to 5 times with exponential backoff on rate limit errors.
    """
    import time

    for attempt in range(5):
        df = yf.download(
            TICKERS,
            start=START_DATE,
            end=END_DATE,
            auto_adjust=True,
            progress=False,
        )
        if not df.empty:
            df.dropna(how="all", inplace=True)
            return df
        wait = 10 * (2 ** attempt)  # 10s, 20s, 40s, 80s, 160s
        time.sleep(wait)

    return pd.DataFrame()


def get_close(df: pd.DataFrame) -> pd.DataFrame:
    """Extract Close prices as a simple (date x ticker) DataFrame."""
    close = df["Close"].copy()
    close.columns = [TICKER_LABELS[t] for t in close.columns]
    close.dropna(inplace=True)
    return close


def get_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Extract Volume as a simple (date x ticker) DataFrame."""
    vol = df["Volume"].copy()
    vol.columns = [TICKER_LABELS[t] for t in vol.columns]
    return vol


def get_ohlcv(df: pd.DataFrame, ticker_sa: str) -> pd.DataFrame:
    """Return OHLCV for a single ticker (e.g. 'PETR4.SA')."""
    result = pd.DataFrame({
        "Open":   df["Open"][ticker_sa],
        "High":   df["High"][ticker_sa],
        "Low":    df["Low"][ticker_sa],
        "Close":  df["Close"][ticker_sa],
        "Volume": df["Volume"][ticker_sa],
    })
    result.dropna(inplace=True)
    return result


def normalize_prices(close: pd.DataFrame) -> pd.DataFrame:
    """Rebase each column so the first non-NaN value = 100."""
    return close.div(close.iloc[0]) * 100


def compute_metrics(close: pd.DataFrame, volume: pd.DataFrame, ticker_label: str) -> dict:
    """Return a dict of key metrics for one ticker."""
    prices = close[ticker_label].dropna()
    vols = volume[ticker_label].dropna()

    if prices.empty:
        return {}

    current_price = float(prices.iloc[-1])
    first_price = float(prices.iloc[0])
    returns_pct = (current_price / first_price - 1) * 100
    daily_returns = prices.pct_change().dropna()
    annualized_vol = float(daily_returns.std() * np.sqrt(252) * 100)

    return {
        "current_price": current_price,
        "returns_pct": returns_pct,
        "max_price": float(prices.max()),
        "min_price": float(prices.min()),
        "avg_volume": float(vols.mean()),
        "annualized_vol": annualized_vol,
    }
