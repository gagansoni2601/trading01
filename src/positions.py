"""
Paper-trading position tracker + decision log.

This is what powers the "end of day results for decisions taken by the
rules" feature: every time the screener runs, it
  1. Opens a new tracked (paper) position for every stock that newly
     qualifies under the entry rules (if AUTO_PAPER_TRADE is on and there's
     room under MAX_OPEN_POSITIONS).
  2. Re-checks every currently open position against the exit rules, and
     closes any that trigger (logging the reason and the resulting P&L).
  3. Appends every decision (ENTRY / HOLD / EXIT / SKIPPED) to a permanent
     decision_log.csv so you can see exactly what the bot decided and why,
     on any given day.
  4. Produces a markdown End-of-Day report summarizing today's decisions
     plus running performance stats (win rate, avg return, open vs closed).

State is stored in plain CSVs under data/ so it persists across runs (and
across GitHub Actions runs, as long as the workflow commits the data/ folder
back to the repo — see .github/workflows/daily_screener.yml).
"""

import os
import datetime as dt
import pandas as pd

from . import config

POSITIONS_COLUMNS = [
    "Symbol", "EntryDate", "EntryPrice", "EntryATR14", "Status",
    "ExitDate", "ExitPrice", "ExitReason", "ReturnPct",
]

DECISION_LOG_COLUMNS = [
    "Date", "Symbol", "Decision", "Price", "SignalStrength_%",
    "EntryRulesPassed", "BonusScore", "Reason",
]


def _ensure_dirs():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    os.makedirs(config.SCREENER_RESULTS_DIR, exist_ok=True)


def load_positions():
    _ensure_dirs()
    if os.path.exists(config.POSITIONS_CSV):
        df = pd.read_csv(config.POSITIONS_CSV)
    else:
        df = pd.DataFrame(columns=POSITIONS_COLUMNS)
    # Force object dtype on columns that mix strings/NaN so pandas doesn't
    # infer them as float64 when empty (which then errors on string writes).
    for col in ("EntryDate", "Status", "ExitDate", "ExitReason"):
        if col in df.columns:
            df[col] = df[col].astype(object).where(df[col].notna(), None)
    for col in ("EntryPrice", "EntryATR14", "ExitPrice", "ReturnPct"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def save_positions(df):
    _ensure_dirs()
    df.to_csv(config.POSITIONS_CSV, index=False)


def append_decision_log(rows):
    """rows: list of dicts matching DECISION_LOG_COLUMNS."""
    _ensure_dirs()
    new_df = pd.DataFrame(rows, columns=DECISION_LOG_COLUMNS)
    if os.path.exists(config.DECISION_LOG_CSV):
        existing = pd.read_csv(config.DECISION_LOG_CSV)
        out = pd.concat([existing, new_df], ignore_index=True)
    else:
        out = new_df
    out.to_csv(config.DECISION_LOG_CSV, index=False)


def process_decisions(screener_results, exit_evaluator):
    """
    Core daily decision pipeline.

    screener_results: list of dicts from rules.analyze_stock() for every
                       stock screened today.
    exit_evaluator: function(symbol, entry_price, entry_atr) -> dict from
                     rules.evaluate_exit() using *today's* indicator values
                     for that symbol. Passed in to avoid re-fetching data.

    Returns: (positions_df, decision_rows, today_str)
    """
    today_str = dt.date.today().strftime("%Y-%m-%d")
    positions = load_positions()
    decision_rows = []

    results_by_symbol = {r["Symbol"]: r for r in screener_results}

    # ---- 1. Check existing open positions for exit signals ----
    open_mask = positions["Status"] == "OPEN"
    for idx in positions[open_mask].index:
        sym = positions.at[idx, "Symbol"]
        entry_price = positions.at[idx, "EntryPrice"]
        entry_atr = positions.at[idx, "EntryATR14"]
        exit_result = exit_evaluator(sym, entry_price, entry_atr)
        if exit_result is None:
            continue  # couldn't fetch data today, leave position open
        if exit_result["ExitTriggered"]:
            close_price = exit_result.get("ClosePrice")
            positions.at[idx, "Status"] = "CLOSED"
            positions.at[idx, "ExitDate"] = today_str
            positions.at[idx, "ExitPrice"] = close_price
            positions.at[idx, "ExitReason"] = exit_result["ExitReason"]
            ret_pct = round((close_price - entry_price) / entry_price * 100, 2)
            positions.at[idx, "ReturnPct"] = ret_pct
            decision_rows.append({
                "Date": today_str, "Symbol": sym, "Decision": "EXIT",
                "Price": close_price, "SignalStrength_%": None,
                "EntryRulesPassed": None, "BonusScore": None,
                "Reason": f"{exit_result['ExitReason']} (return {ret_pct}%)",
            })
        else:
            decision_rows.append({
                "Date": today_str, "Symbol": sym, "Decision": "HOLD",
                "Price": exit_result.get("ClosePrice"), "SignalStrength_%": None,
                "EntryRulesPassed": None, "BonusScore": None,
                "Reason": f"gain {exit_result['CurrentGainPct']}%, no exit trigger",
            })

    # ---- 2. Open new positions for stocks that qualify today ----
    open_symbols = set(positions[positions["Status"] == "OPEN"]["Symbol"])
    n_open = len(open_symbols)

    for r in screener_results:
        sym = r["Symbol"]
        if sym in open_symbols:
            continue  # already holding, don't double-enter
        if r["Qualifies"]:
            if config.AUTO_PAPER_TRADE and n_open < config.MAX_OPEN_POSITIONS:
                new_row = {
                    "Symbol": sym, "EntryDate": today_str, "EntryPrice": r["Close"],
                    "EntryATR14": r["ATR14"], "Status": "OPEN",
                    "ExitDate": None, "ExitPrice": None, "ExitReason": None,
                    "ReturnPct": None,
                }
                positions = pd.concat([positions, pd.DataFrame([new_row])], ignore_index=True)
                n_open += 1
                decision_rows.append({
                    "Date": today_str, "Symbol": sym, "Decision": "ENTRY",
                    "Price": r["Close"], "SignalStrength_%": r["SignalStrength_%"],
                    "EntryRulesPassed": r["EntryRulesPassed"], "BonusScore": r["BonusScore"],
                    "Reason": "All entry rules + bonus + signal strength threshold met",
                })
            else:
                decision_rows.append({
                    "Date": today_str, "Symbol": sym, "Decision": "QUALIFIED_NOT_TAKEN",
                    "Price": r["Close"], "SignalStrength_%": r["SignalStrength_%"],
                    "EntryRulesPassed": r["EntryRulesPassed"], "BonusScore": r["BonusScore"],
                    "Reason": "Qualified but MAX_OPEN_POSITIONS reached or auto-trade disabled",
                })

    save_positions(positions)
    append_decision_log(decision_rows)
    return positions, decision_rows, today_str


def build_eod_report(positions, decision_rows, today_str, screened_count):
    entries = [d for d in decision_rows if d["Decision"] == "ENTRY"]
    exits = [d for d in decision_rows if d["Decision"] == "EXIT"]
    holds = [d for d in decision_rows if d["Decision"] == "HOLD"]
    qualified_not_taken = [d for d in decision_rows if d["Decision"] == "QUALIFIED_NOT_TAKEN"]

    closed = positions[positions["Status"] == "CLOSED"]
    open_pos = positions[positions["Status"] == "OPEN"]
    win_count = (closed["ReturnPct"] > 0).sum() if len(closed) else 0
    win_rate = round(100 * win_count / len(closed), 1) if len(closed) else None
    avg_return = round(closed["ReturnPct"].mean(), 2) if len(closed) else None

    lines = []
    lines.append(f"# End-of-Day Screener Report — {today_str}\n")
    lines.append(f"- Stocks screened: **{screened_count}**")
    lines.append(f"- New entries today: **{len(entries)}**")
    lines.append(f"- Exits today: **{len(exits)}**")
    lines.append(f"- Positions held (no exit trigger): **{len(holds)}**")
    lines.append(f"- Qualified but not taken (cap reached): **{len(qualified_not_taken)}**")
    lines.append(f"- Currently open positions: **{len(open_pos)}**")
    lines.append(f"- Closed trades (all-time): **{len(closed)}**, "
                  f"Win rate: **{win_rate if win_rate is not None else 'n/a'}%**, "
                  f"Avg return/trade: **{avg_return if avg_return is not None else 'n/a'}%**\n")

    if entries:
        lines.append("## New Entries Today")
        lines.append("| Symbol | Price | Signal % | Entry Rules | Bonus |")
        lines.append("|---|---|---|---|---|")
        for d in entries:
            lines.append(f"| {d['Symbol']} | {d['Price']} | {d['SignalStrength_%']} | "
                          f"{d['EntryRulesPassed']} | {d['BonusScore']} |")
        lines.append("")

    if exits:
        lines.append("## Exits Today")
        lines.append("| Symbol | Exit Price | Reason |")
        lines.append("|---|---|---|")
        for d in exits:
            lines.append(f"| {d['Symbol']} | {d['Price']} | {d['Reason']} |")
        lines.append("")

    if len(open_pos):
        lines.append("## Currently Open Positions")
        lines.append("| Symbol | Entry Date | Entry Price | Days Held |")
        lines.append("|---|---|---|---|")
        for _, row in open_pos.iterrows():
            try:
                days_held = (dt.date.today() - dt.datetime.strptime(row["EntryDate"], "%Y-%m-%d").date()).days
            except Exception:
                days_held = "n/a"
            lines.append(f"| {row['Symbol']} | {row['EntryDate']} | {row['EntryPrice']} | {days_held} |")
        lines.append("")

    if qualified_not_taken:
        lines.append("## Qualified But Not Taken (position cap reached)")
        lines.append("| Symbol | Price | Signal % |")
        lines.append("|---|---|---|")
        for d in qualified_not_taken:
            lines.append(f"| {d['Symbol']} | {d['Price']} | {d['SignalStrength_%']} |")
        lines.append("")

    report_text = "\n".join(lines)
    _ensure_dirs()
    report_path = os.path.join(config.REPORTS_DIR, f"eod_report_{today_str}.md")
    with open(report_path, "w") as f:
        f.write(report_text)
    # also keep a rolling "latest" copy for easy linking
    latest_path = os.path.join(config.REPORTS_DIR, "latest.md")
    with open(latest_path, "w") as f:
        f.write(report_text)
    return report_text, report_path
