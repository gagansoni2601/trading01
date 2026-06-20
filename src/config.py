"""Central configuration for the Nifty 100 screener."""

import os

# ---- Indicator / rule parameters ----
LOOKBACK_DAYS = 250
RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14
EMA_FAST = 20
EMA_SLOW = 50
HH_LOOKBACK = 20
VOL_LOOKBACK = 20
VOL_MULTIPLIER = 1.5
RSI_ENTRY_MIN = 60
RSI_EXIT_MAX = 50
ATR_STOP_MULTIPLIER = 2
PROFIT_TARGET_LOW = 0.10
PROFIT_TARGET_HIGH = 0.15
ADX_BONUS_THRESHOLD = 25
MIN_BONUS_SCORE = 2
SIGNAL_THRESHOLD_PCT = 70  # composite "signal strength" needed to trigger an alert

NIFTY50_TICKER = "^NSEI"

# ---- Paper-trading / decision tracking ----
# If True, every stock that clears the entry rules is automatically logged
# as a new open paper position (so the bot can track and report on its own
# decisions over time). Set False if you only want alerts, no auto-tracking.
AUTO_PAPER_TRADE = True
MAX_OPEN_POSITIONS = 15  # cap so the bot doesn't open unlimited positions

# ---- Notification ----
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---- File paths ----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CONSTITUENTS_CSV = os.path.join(DATA_DIR, "nifty100_constituents.csv")
POSITIONS_CSV = os.path.join(DATA_DIR, "positions.csv")
DECISION_LOG_CSV = os.path.join(DATA_DIR, "decision_log.csv")
SCREENER_RESULTS_DIR = os.path.join(DATA_DIR, "screener_results")

# Best-effort fallback Nifty 100 list (used only if data/nifty100_constituents.csv
# is missing). NSE rebalances this index every 6 months — for guaranteed
# accuracy, download the official list from:
# https://niftyindices.com/IndexConstituent/ind_nifty100list.csv
# and save it as data/nifty100_constituents.csv
NIFTY100_FALLBACK = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BPCL", "BHARTIARTL",
    "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
    "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
    "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC",
    "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LTIM",
    "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND",
    "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
    "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS", "TATASTEEL",
    "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO",
    "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "DLF", "GODREJCP",
    "HAVELLS", "ICICIGIBANK", "ICICIPRULI", "INDIGO", "IOC",
    "IRCTC", "JINDALSTEL", "LICI", "NAUKRI", "PIDILITIND",
    "PNB", "SHREECEM", "SIEMENS", "TATAPOWER", "TORNTPHARM",
    "TVSMOTOR", "VEDL", "ZOMATO", "ZYDUSLIFE", "ABB",
    "ACC", "ALKEM", "AUROPHARMA", "BANDHANBNK", "BANKBARODA",
    "BERGEPAINT", "BEL", "BOSCHLTD", "CANBK", "CHOLAFIN",
    "COLPAL", "CONCOR", "DABUR", "DIXON", "GAIL",
    "GODREJPROP", "HDFCAMC", "IDFCFIRSTB", "INDHOTEL", "INDUSTOWER",
    "MARICO", "MOTHERSON", "MUTHOOTFIN", "PAGEIND", "PEL",
    "PFC", "RECLTD", "SRF", "TRENT", "UNITDSPR",
]
