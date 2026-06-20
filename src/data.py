"""Data fetching helpers (Yahoo Finance via yfinance)."""

import os
import pandas as pd
import yfinance as yf

from . import config


def load_nifty100_symbols():
    """Load symbols from data/nifty100_constituents.csv if present, else
    fall back to the built-in snapshot list in config.py."""
    if os.path.exists(config.CONSTITUENTS_CSV):
        try:
            df = pd.read_csv(config.CONSTITUENTS_CSV)
            col = "Symbol" if "Symbol" in df.columns else df.columns[0]
            symbols = df[col].astype(str).str.strip().tolist()
            print(f"Loaded {len(symbols)} symbols from {config.CONSTITUENTS_CSV}")
            return symbols
        except Exception as e:
            print(f"Could not read {config.CONSTITUENTS_CSV} ({e}), using fallback list.")
    print(f"Using built-in fallback list of {len(config.NIFTY100_FALLBACK)} symbols. "
          f"For guaranteed up-to-date constituents, download "
          f"https://niftyindices.com/IndexConstituent/ind_nifty100list.csv "
          f"and save it as data/nifty100_constituents.csv")
    return config.NIFTY100_FALLBACK


def fetch_history(ticker, period_days=config.LOOKBACK_DAYS):
    """Fetch daily OHLCV for a single ticker via yfinance."""
    try:
        df = yf.Ticker(ticker).history(period=f"{period_days}d", interval="1d", auto_adjust=False)
        if df is None or df.empty or len(df) < 60:
            return None
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception as e:
        print(f"  [WARN] Failed to fetch {ticker}: {e}")
        return None


def fetch_nifty50_returns(period_days=config.LOOKBACK_DAYS):
    df = fetch_history(config.NIFTY50_TICKER, period_days)
    if df is None:
        return None
    return df["Close"].pct_change()


def to_yf_ticker(symbol):
    return symbol if symbol.endswith(".NS") else f"{symbol}.NS"
