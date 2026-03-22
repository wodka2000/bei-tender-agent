"""Telegram notifier: sends new tender alerts via Telegram Bot API."""

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, WEBAPP_URL

TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _send_message(text: str, reply_markup: dict = None) -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(f"{TELEGRAM_API_BASE}/sendMessage", json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"  [!] Telegram notification failed: {e}")
        return False


def answer_callback(callback_query_id: str, text: str = "") -> None:
    """Acknowledge a Telegram inline button press."""
    try:
        requests.post(
            f"{TELEGRAM_API_BASE}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5,
        )
    except requests.RequestException:
        pass


def remove_inline_keyboard(chat_id: str, message_id: int) -> None:
    """Remove the inline keyboard from a previously sent message."""
    try:
        requests.post(
            f"{TELEGRAM_API_BASE}/editMessageReplyMarkup",
            json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
            timeout=5,
        )
    except requests.RequestException:
        pass


def _format_tender(t: dict) -> str:
    """Format a single tender as an HTML Telegram message."""
    title = t.get("title") or "N/A"
    buyer = t.get("buyer") or "N/A"
    country = t.get("country") or "N/A"
    deadline = t.get("deadline") or "N/A"
    source = t.get("source") or "TED"
    link = t.get("link") or t.get("source_url") or ""
    cpv = t.get("cpv") or t.get("cpv_codes") or ""

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


def _ignore_button(tender_id: str) -> dict:
    """Build an inline keyboard with a single Ignora button."""
    # Callback data max 64 bytes — truncate ID if needed
    callback_data = f"ignore:{tender_id}"[:64]
    return {"inline_keyboard": [[{"text": "Ignora 🚫", "callback_data": callback_data}]]}


def notify_new_tenders(new_tenders: list[dict]) -> None:
    """
    Send Telegram notifications for new tenders with an Ignora button.
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
        tid = t.get("id", "")
        _send_message(_format_tender(t), reply_markup=_ignore_button(tid))

    if WEBAPP_URL:
        _send_message(f'🌐 <a href="{WEBAPP_URL}">Apri tutte le gare</a>')

    print(f"  Telegram: {count} notifica/e inviata/e.")
