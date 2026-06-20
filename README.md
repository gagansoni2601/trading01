# Nifty 100 Momentum Breakout Screener

Automated screener that scans Nifty 100 stocks daily for momentum breakout
setups, **tracks every decision it makes as a paper trade**, and sends you a
notification — including an end-of-day decision summary — automatically via
GitHub Actions. No server required.

## What it checks

**Entry rules (all 5 must pass):**
1. Close > 50 EMA
2. 20 EMA > 50 EMA
3. RSI(14) > 60
4. Today's Volume > 1.5 x 20-day Average Volume
5. Close > Highest High of the last 20 days (fresh breakout)

**Bonus score (need >= 2 of 3):**
- ADX(14) > 25 (trend strength)
- MACD Histogram > 0 (momentum confirmation)
- Relative Strength vs Nifty 50 positive (outperforming the index)

**Composite "Signal Strength"** = (entry rules passed + bonus points) / 8 x
100. A stock triggers an alert only if it passes **all 5 entry rules**, has
**>= 2 bonus points**, and **Signal Strength >= 70%**.

**Exit rules** (any one triggers a close on a tracked position):
- Close < 20 EMA, OR
- RSI(14) < 50, OR
- Price falls 2 x ATR(14) below entry (stop loss), OR
- Profit target of 10% reached

## NEW: Decision tracking & End-of-Day report

Every day the bot runs, it doesn't just alert — it **acts on its own
signals as paper trades** and remembers what it did:

- Stocks that qualify get auto-logged as an **open position**
  (`data/positions.csv`) at that day's close price.
- Every open position is re-checked against the exit rules each day; if
  triggered, it's closed and the reason + return % is recorded.
- Every decision (ENTRY / HOLD / EXIT / QUALIFIED_NOT_TAKEN) is appended to
  a permanent audit trail: `data/decision_log.csv`.
- An **End-of-Day report** (`reports/eod_report_<date>.md`, plus a rolling
  `reports/latest.md`) is generated each run, showing:
  - How many stocks were screened
  - New entries / exits taken today, with reasons
  - All currently open positions and how long they've been held
  - Running performance: win rate and average return across all closed
    trades so far
- A condensed version of this report is also sent as a second Telegram
  notification.

This turns the screener from a one-off alert tool into a running, auditable
record of "what would I have done if I'd followed these rules every day."

Set `AUTO_PAPER_TRADE = False` in `src/config.py` if you only want alerts
with no position tracking.

## Project structure

```
nifty100-screener/
├── .github/workflows/daily_screener.yml   # runs the screener automatically every weekday
├── data/
│   ├── nifty100_constituents.csv          # (you provide) official Nifty 100 list
│   ├── positions.csv                      # tracked paper positions (auto-updated)
│   ├── decision_log.csv                   # full audit trail of every decision (auto-updated)
│   └── screener_results/                  # full daily indicator dumps for every stock
├── reports/
│   ├── eod_report_<date>.md               # daily end-of-day report (auto-generated)
│   └── latest.md                          # always the most recent report
├── src/
│   ├── config.py        # all rule thresholds, file paths, Nifty 100 fallback list
│   ├── data.py           # Yahoo Finance data fetching
│   ├── indicators.py      # EMA/RSI/ATR/ADX/MACD calculations
│   ├── rules.py          # entry/exit/bonus rule evaluation
│   ├── positions.py      # paper-trading tracker + EOD report builder
│   └── notify.py         # Telegram notifications
├── run_screener.py        # main entry point — run this
├── requirements.txt
└── README.md
```

## Deploying this on GitHub (recommended — runs automatically, free)

1. **Create a new GitHub repo** and push this project to it:
   ```bash
   cd nifty100-screener
   git init
   git add .
   git commit -m "Initial commit: Nifty 100 screener"
   git branch -M main
   git remote add origin https://github.com/<your-username>/nifty100-screener.git
   git push -u origin main
   ```

2. **Add the official Nifty 100 list** (recommended for accuracy):
   - Download https://niftyindices.com/IndexConstituent/ind_nifty100list.csv
   - Save it as `data/nifty100_constituents.csv` in your repo, commit & push.
   - (NSE rebalances this index roughly every 6 months — refresh this file
     periodically. Without it, the script falls back to a built-in snapshot
     list which can drift out of date.)

3. **(Optional) Set up Telegram alerts:**
   - Message **@BotFather** on Telegram → `/newbot` → get a **bot token**.
   - Message **@userinfobot** → get your numeric **chat ID**.
   - In your GitHub repo: **Settings → Secrets and variables → Actions →
     New repository secret**, add:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHAT_ID`
   - Without these, the bot still runs and commits results/reports to the
     repo — you just won't get a push notification, you'd check
     `reports/latest.md` in the repo instead.

4. **Enable GitHub Actions** (usually on by default for new repos): go to
   the **Actions** tab in your repo, you should see "Daily Nifty 100
   Screener" listed. Click **Run workflow** to trigger it manually and
   confirm it works.

5. **Done.** It will now run automatically every weekday at 16:05 IST,
   screen all stocks, update `data/positions.csv` and
   `data/decision_log.csv`, write a new `reports/eod_report_<date>.md`, and
   commit everything back to your repo — plus send Telegram alerts if
   configured.

You can change the schedule by editing the `cron:` line in
`.github/workflows/daily_screener.yml` (uses UTC time).

## Running it locally instead

```bash
pip install -r requirements.txt
python run_screener.py
```

Optionally export Telegram credentials first:
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-yourtoken"
export TELEGRAM_CHAT_ID="123456789"
```

## Notes & assumptions

- Data comes from Yahoo Finance via the free `yfinance` library — typically
  end-of-day for Indian equities, with occasional rate-limiting if run too
  frequently. Free, no broker login needed, but not tick-by-tick real-time.
- **"Profit opportunity > 70%"** from the original brief was interpreted as
  the composite **Signal Strength** score (entry rules + bonus points,
  normalized to 0-100%) described above. If you meant a different
  metric — e.g. a backtested expected-return model or a specific
  probability-of-target-hit calculation — let me know and the formula in
  `src/rules.py` can be adjusted.
- The position tracker is a **paper-trading simulation** for decision
  auditing purposes only — it does not place real trades or connect to a
  broker. If you want it to execute real orders, that would need a broker
  API integration (e.g. Zerodha Kite Connect, Upstox), which is a
  significant additional step involving real money risk — happy to help if
  you want to go that route deliberately.
- `MAX_OPEN_POSITIONS` (default 15) caps how many paper positions are open
  at once so the bot doesn't pile into every breakout; adjust in
  `src/config.py`.
- This is a technical screening tool, not financial advice. Past
  performance shown in the EOD reports (including paper-traded results) is
  not indicative of future results.
