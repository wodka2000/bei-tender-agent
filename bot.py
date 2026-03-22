"""
Telegram bot con polling: ascolta comandi e lancia il tender check su richiesta.

Comandi supportati:
  /check  — esegue subito la ricerca di nuove gare
  /status — mostra quante gare sono tracciate
  /gare   — lista le gare aperte non ancora ignorate
"""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from notifier import _send_message, _format_tender, _ignore_button, answer_callback, remove_inline_keyboard

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

_check_running = False


def get_updates(offset: int) -> list[dict]:
    try:
        resp = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params={"timeout": 30, "offset": offset},
            timeout=35,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    except requests.RequestException:
        return []


def handle_callback(callback_query: dict) -> None:
    """Handle inline keyboard button presses."""
    cq_id = callback_query.get("id", "")
    data = callback_query.get("data", "")
    msg = callback_query.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    message_id = msg.get("message_id")

    if data.startswith("check_source:"):
        source = data[len("check_source:"):]
        sources = None if source == "ALL" else [source]
        label = "tutte le fonti" if source == "ALL" else source
        answer_callback(cq_id, f"Avvio ricerca: {label}")
        if message_id:
            remove_inline_keyboard(chat_id, message_id)

        def run_check(srcs=sources, lbl=label):
            global _check_running
            if _check_running:
                _send_message("⏳ Ricerca già in corso, attendi...")
                return
            _check_running = True
            _send_message(f"🔍 Ricerca in corso: {lbl}...")
            try:
                from main import main
                main(sources=srcs)
                _send_message("✅ Ricerca completata.")
            except Exception as e:
                _send_message(f"❌ Errore:\n<code>{e}</code>")
            finally:
                _check_running = False

        threading.Thread(target=run_check, daemon=True).start()

    elif data.startswith("ignore:"):
        tender_id = data[len("ignore:"):]
        try:
            from storage import mark_tender_ignored
            mark_tender_ignored(tender_id)
            answer_callback(cq_id, "Gara ignorata ✓")
            if message_id:
                remove_inline_keyboard(chat_id, message_id)
        except Exception as e:
            answer_callback(cq_id, "Errore")
            print(f"  [!] Errore ignore callback: {e}")


def handle_command(text: str) -> None:
    text = text.strip().lower()

    if text.startswith("/check"):
        if _check_running:
            _send_message("⏳ Ricerca già in corso, attendi...")
            return

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "TED", "callback_data": "check_source:TED"},
                    {"text": "EIB", "callback_data": "check_source:EIB"},
                    {"text": "World Bank", "callback_data": "check_source:World Bank"},
                ],
                [
                    {"text": "ANAC", "callback_data": "check_source:ANAC"},
                    {"text": "Bahrain", "callback_data": "check_source:Bahrain"},
                    {"text": "Tunisia", "callback_data": "check_source:Tunisia"},
                ],
                [
                    {"text": "✅ Tutte le fonti", "callback_data": "check_source:ALL"},
                ],
            ]
        }
        _send_message("🔍 Quale fonte vuoi monitorare?", reply_markup=keyboard)

    elif text.startswith("/gare"):
        try:
            from storage import load_seen_tenders, load_ignored_tenders, compute_status, normalize_deadline
            seen = load_seen_tenders()
            ignored = load_ignored_tenders()

            open_tenders = [
                {"id": tid, **info}
                for tid, info in seen.items()
                if tid not in ignored
                and compute_status(normalize_deadline(info.get("deadline", ""))) != "Closed"
            ]
            open_tenders.sort(key=lambda t: t.get("deadline") or "", reverse=False)

            if not open_tenders:
                _send_message("✅ Nessuna gara aperta al momento.")
                return

            _send_message(f"📋 <b>{len(open_tenders)} gare aperte</b> (non ignorate):")
            for t in open_tenders[:15]:  # max 15 per non spammare
                _send_message(_format_tender(t), reply_markup=_ignore_button(t["id"]))
            if len(open_tenders) > 15:
                _send_message(f"... e altre {len(open_tenders) - 15} gare. Usa la web app per vederle tutte.")

        except Exception as e:
            _send_message(f"❌ Errore:\n<code>{e}</code>")

    elif text.startswith("/status"):
        try:
            from storage import load_seen_tenders, load_ignored_tenders
            seen = load_seen_tenders()
            ignored = load_ignored_tenders()
            open_count = sum(1 for t in seen.values() if t.get("status") == "Open")
            _send_message(
                f"📊 <b>Stato attuale</b>\n\n"
                f"Gare tracciate: {len(seen)}\n"
                f"Ancora aperte: {open_count}\n"
                f"Ignorate: {len(ignored)}"
            )
        except Exception as e:
            _send_message(f"❌ Errore:\n<code>{e}</code>")

    elif text.startswith("/start") or text.startswith("/help"):
        _send_message(
            "👋 <b>BEI Tender Agent</b>\n\n"
            "Comandi disponibili:\n"
            "/check — cerca nuove gare adesso\n"
            "/gare — mostra tutte le gare aperte\n"
            "/status — riepilogo numerico"
        )


def run_bot() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID non configurati.")
        return

    print("Bot in ascolto... (Ctrl+C per fermare)")
    _send_message("✅ Bot avviato. Scrivi /help per i comandi.")

    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1

            # Gestione bottoni inline
            if "callback_query" in update:
                cq = update["callback_query"]
                cq_chat_id = str(cq.get("message", {}).get("chat", {}).get("id", ""))
                if cq_chat_id == str(TELEGRAM_CHAT_ID):
                    handle_callback(cq)
                continue

            # Gestione comandi testuali
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id != str(TELEGRAM_CHAT_ID):
                continue
            text = msg.get("text", "")
            if text:
                print(f"  Comando ricevuto: {text}")
                handle_command(text)

        time.sleep(1)


def run_health_server() -> None:
    """Mini HTTP server per soddisfare Render (richiede una porta aperta)."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        def log_message(self, *args):
            pass

    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    run_bot()
