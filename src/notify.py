"""Notification sending (Telegram, with console/file fallback)."""

import requests

from . import config


def send_telegram(message):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[WARN] Telegram send failed: {e}")
        return False


def build_alert_message(qualifying):
    import datetime as dt
    today = dt.date.today().strftime("%d-%b-%Y")
    lines = [f"*Nifty 100 Breakout Screener — {today}*", f"{len(qualifying)} stock(s) qualified:\n"]
    for r in qualifying:
        lines.append(
            f"*{r['Symbol']}* — CMP {r['Close']} | RSI {r['RSI14']} | "
            f"Signal {r['SignalStrength_%']}% | Bonus {r['BonusScore']}\n"
            f"  SL: {r['SuggestedStopLoss']}  |  Target: {r['SuggestedTarget_10to15pct']}"
        )
    return "\n".join(lines)


def build_eod_telegram_summary(report_text, max_len=3500):
    """Telegram messages are capped (~4096 chars). Trim the markdown report
    to a safe length for chat delivery; the full report is always available
    in the repo's reports/ folder."""
    header = "*End-of-Day Decision Summary*\n\n"
    body = report_text
    if len(header) + len(body) > max_len:
        body = body[: max_len - len(header) - 20] + "\n\n...(see full report in repo)"
    return header + body
