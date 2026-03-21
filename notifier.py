"""Telegram notifier: sends new tender alerts via Telegram Bot API."""

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _send_message(text: str) -> bool:
    """Send a single message to the configured Telegram chat. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  [!] Telegram notification failed: {e}")
        return False


def _format_tender(t: dict) -> str:
    """Format a single tender as an HTML Telegram message."""
    title = t.get("title") or "N/A"
    buyer = t.get("buyer") or "N/A"
    country = t.get("country") or "N/A"
    deadline = t.get("deadline") or "N/A"
    source = t.get("source") or "TED"
    link = t.get("link") or ""
    cpv = t.get("cpv") or ""

    lines = [
        f"🔔 <b>{title}</b>",
        "",
        f"🏦 <b>Buyer:</b> {buyer}",
        f"🌍 <b>Paese:</b> {country}",
        f"📅 <b>Scadenza:</b> {deadline}",
        f"📂 <b>Fonte:</b> {source}",
    ]
    if cpv:
        lines.append(f"🏷 <b>CPV:</b> {cpv}")
    if link:
        lines.append(f'🔗 <a href="{link}">Apri gara</a>')

    return "\n".join(lines)


def notify_new_tenders(new_tenders: list[dict]) -> None:
    """
    Send Telegram notifications for new tenders.
    Does nothing if TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID are not set.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [i] Telegram not configured — skipping notifications.")
        return

    if not new_tenders:
        return

    count = len(new_tenders)
    header = f"📋 <b>BEI Tender Agent</b>\n\n{count} nuov{'a gara trovata' if count == 1 else 'e gare trovate'}."
    _send_message(header)

    for t in new_tenders:
        _send_message(_format_tender(t))

    print(f"  Telegram: {count} notifica/e inviata/e.")
