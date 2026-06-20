#!/usr/bin/env python3
"""
Nifty 100 Momentum Breakout Screener — main entry point.

Run this daily (manually or via the included GitHub Actions workflow,
.github/workflows/daily_screener.yml) after market close.

Each run:
  1. Screens all Nifty 100 stocks against the entry rules + bonus score.
  2. Sends a real-time alert for stocks that newly qualify (Signal
     Strength >= threshold).
  3. Updates the paper-trading position tracker: opens new tracked
     positions, closes ones that hit an exit rule.
  4. Writes an End-of-Day report (reports/eod_report_<date>.md) showing
     every decision taken today plus running performance stats, and sends
     a condensed version as a second notification.

See README.md for setup.
"""

import datetime as dt
import time

from src import config
from src import data
from src import rules
from src import notify
from src import positions as pos_module


def run():
    symbols = data.load_nifty100_symbols()
    print("Fetching Nifty 50 index data for relative strength comparison...")
    nifty50_returns = data.fetch_nifty50_returns()

    results = []
    raw_dfs = {}  # keep computed-indicator dfs around for exit evaluation reuse
    print(f"Analyzing {len(symbols)} stocks...\n")
    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym} ...", end=" ")
        ticker = data.to_yf_ticker(sym)
        df = data.fetch_history(ticker)
        res = rules.analyze_stock(sym, df, nifty50_returns)
        if res:
            results.append(res)
            if df is not None:
                raw_dfs[sym] = rules.compute_indicators(df)
            print(f"Signal {res['SignalStrength_%']}% | Qualifies: {res['Qualifies']}")
        else:
            print("skipped (insufficient data)")
        time.sleep(0.3)  # be gentle on Yahoo Finance rate limits

    if not results:
        print("No data could be retrieved. Check your internet connection / yfinance status.")
        return

    # ---- Save full raw results ----
    import pandas as pd
    import os
    today_str = dt.date.today().strftime("%Y%m%d")
    os.makedirs(config.SCREENER_RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(config.SCREENER_RESULTS_DIR, f"screener_results_{today_str}.csv")
    pd.DataFrame(results).sort_values("SignalStrength_%", ascending=False).to_csv(out_csv, index=False)
    print(f"\nFull results saved to {out_csv}")

    # ---- Real-time qualifying alert ----
    qualifying = sorted([r for r in results if r["Qualifies"]],
                         key=lambda r: r["SignalStrength_%"], reverse=True)
    print(f"\n{'='*60}\n{len(qualifying)} stock(s) qualify for entry\n{'='*60}")
    for r in qualifying:
        print(f"  {r['Symbol']:<15} CMP={r['Close']:<10} Signal={r['SignalStrength_%']}%")

    if qualifying:
        sent = notify.send_telegram(notify.build_alert_message(qualifying))
        print("✅ Telegram entry alert sent." if sent else "(Telegram not configured for entry alert.)")

    # ---- Exit evaluator closure: re-uses today's already-fetched indicator data ----
    def exit_evaluator(symbol, entry_price, entry_atr):
        df = raw_dfs.get(symbol)
        if df is None:
            return None
        last = df.iloc[-1]
        result = rules.evaluate_exit(last, entry_price, entry_atr)
        result["ClosePrice"] = round(last["Close"], 2)
        return result

    # ---- Decision tracking + EOD report (the new feature) ----
    positions_df, decision_rows, today_iso = pos_module.process_decisions(results, exit_evaluator)
    report_text, report_path = pos_module.build_eod_report(positions_df, decision_rows, today_iso, len(results))
    print(f"\nEnd-of-day report written to {report_path}")

    eod_sent = notify.send_telegram(notify.build_eod_telegram_summary(report_text))
    print("✅ Telegram EOD summary sent." if eod_sent else "(Telegram not configured for EOD summary.)")

    print("\nDone.")


if __name__ == "__main__":
    run()
