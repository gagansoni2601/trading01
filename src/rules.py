"""Entry/exit rule evaluation and scoring."""

import numpy as np
import pandas as pd

from . import config
from . import indicators as ind


def compute_indicators(df):
    df = df.copy()
    df["EMA20"] = ind.ema(df["Close"], config.EMA_FAST)
    df["EMA50"] = ind.ema(df["Close"], config.EMA_SLOW)
    df["RSI14"] = ind.rsi(df["Close"], config.RSI_PERIOD)
    df["ATR14"] = ind.atr(df, config.ATR_PERIOD)
    df["ADX14"] = ind.adx(df, config.ADX_PERIOD)
    df["MACD_HIST"] = ind.macd_histogram(df["Close"])
    df["AvgVol20"] = df["Volume"].rolling(config.VOL_LOOKBACK).mean()
    df["HH20"] = df["High"].rolling(config.HH_LOOKBACK).max().shift(1)
    return df


def relative_strength_20d(stock_df, nifty50_returns):
    if nifty50_returns is None:
        return None
    try:
        stock_ret_20 = stock_df["Close"].pct_change(20).iloc[-1]
        nifty_ret_20 = (1 + nifty50_returns).rolling(20).apply(np.prod, raw=True).iloc[-1] - 1
        return stock_ret_20 - nifty_ret_20
    except Exception:
        return None


def evaluate_entry(last_row):
    r1 = last_row["Close"] > last_row["EMA50"]
    r2 = last_row["EMA20"] > last_row["EMA50"]
    r3 = last_row["RSI14"] > config.RSI_ENTRY_MIN
    r4 = last_row["Volume"] > config.VOL_MULTIPLIER * last_row["AvgVol20"]
    r5 = last_row["Close"] > last_row["HH20"]
    rules = {"Rule1_CloseAbove50EMA": r1, "Rule2_20EMAabove50EMA": r2,
             "Rule3_RSIover60": r3, "Rule4_VolSurge": r4, "Rule5_Breakout20d": r5}
    passed = sum(rules.values())
    return rules, passed, all(rules.values())


def evaluate_bonus(last_row, rel_strength):
    b_adx = last_row["ADX14"] > config.ADX_BONUS_THRESHOLD
    b_macd = last_row["MACD_HIST"] > 0
    b_rs = (rel_strength is not None) and (rel_strength > 0)
    bonus = int(b_adx) + int(b_macd) + int(b_rs)
    return {"ADX_above_25": b_adx, "MACD_positive": b_macd, "RelStrength_positive": b_rs}, bonus


def evaluate_exit(last_row, entry_price, atr_at_entry=None):
    """Evaluate exit conditions for an open position.
    entry_price: price the paper position was opened at.
    atr_at_entry: ATR14 value captured at entry time (more correct stop-loss
                  basis than today's ATR, but today's ATR is used as fallback).
    """
    atr_val = atr_at_entry if atr_at_entry is not None else last_row["ATR14"]
    e1 = last_row["Close"] < last_row["EMA20"]
    e2 = last_row["RSI14"] < config.RSI_EXIT_MAX
    stop_loss_price = entry_price - config.ATR_STOP_MULTIPLIER * atr_val
    e3 = last_row["Close"] <= stop_loss_price
    pct_gain = (last_row["Close"] - entry_price) / entry_price
    e4 = pct_gain >= config.PROFIT_TARGET_LOW
    triggered = e1 or e2 or e3 or e4
    reason = None
    if e3:
        reason = "STOP_LOSS"
    elif e4:
        reason = "PROFIT_TARGET"
    elif e1:
        reason = "CLOSE_BELOW_EMA20"
    elif e2:
        reason = "RSI_BELOW_50"
    return {
        "ExitTriggered": triggered,
        "ExitReason": reason,
        "Close_below_EMA20": e1,
        "RSI_below_50": e2,
        "StopLossHit": e3,
        "ProfitTargetHit": e4,
        "StopLossPrice": round(stop_loss_price, 2),
        "CurrentGainPct": round(pct_gain * 100, 2),
    }


def signal_strength_pct(entry_passed, bonus):
    total_points = entry_passed + bonus
    return round((total_points / 8) * 100, 1)


def analyze_stock(symbol, df, nifty50_returns):
    if df is None or len(df) < 55:
        return None
    df = compute_indicators(df)
    last = df.iloc[-1]
    if pd.isna(last["EMA50"]) or pd.isna(last["AvgVol20"]) or pd.isna(last["HH20"]):
        return None

    entry_rules, entry_passed, entry_signal = evaluate_entry(last)
    rel_strength = relative_strength_20d(df, nifty50_returns)
    bonus_rules, bonus = evaluate_bonus(last, rel_strength)
    strength_pct = signal_strength_pct(entry_passed, bonus)
    qualifies = entry_signal and bonus >= config.MIN_BONUS_SCORE and strength_pct >= config.SIGNAL_THRESHOLD_PCT

    target_low = round(last["Close"] * (1 + config.PROFIT_TARGET_LOW), 2)
    target_high = round(last["Close"] * (1 + config.PROFIT_TARGET_HIGH), 2)
    stop_loss_price = round(last["Close"] - config.ATR_STOP_MULTIPLIER * last["ATR14"], 2)

    result = {
        "Symbol": symbol,
        "Close": round(last["Close"], 2),
        "EMA20": round(last["EMA20"], 2),
        "EMA50": round(last["EMA50"], 2),
        "RSI14": round(last["RSI14"], 1),
        "ATR14": round(last["ATR14"], 2),
        "ADX14": round(last["ADX14"], 1),
        "MACD_Hist": round(last["MACD_HIST"], 2),
        "Volume": int(last["Volume"]),
        "AvgVol20": int(last["AvgVol20"]),
        "HH20": round(last["HH20"], 2),
        "RelStrength20d_%": round(rel_strength * 100, 2) if rel_strength is not None else None,
        "EntryRulesPassed": f"{entry_passed}/5",
        "EntrySignal": entry_signal,
        "BonusScore": f"{bonus}/3",
        "SignalStrength_%": strength_pct,
        "Qualifies": qualifies,
        "SuggestedStopLoss": stop_loss_price,
        "SuggestedTarget_10to15pct": f"{target_low} - {target_high}",
    }
    result.update(entry_rules)
    result.update(bonus_rules)
    return result
