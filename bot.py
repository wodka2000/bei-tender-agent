"""
Telegram bot con polling: ascolta comandi e lancia il tender check su richiesta.

Comandi supportati:
  /check  — esegue subito la ricerca di nuove gare
  /status — mostra quante gare sono tracciate
"""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from notifier import _send_message

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


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


def handle_command(text: str) -> None:
    text = text.strip().lower()

    if text.startswith("/check"):
        _send_message("🔍 Avvio ricerca gare...")
        try:
            from main import main
            main()
        except Exception as e:
            _send_message(f"❌ Errore durante la ricerca:\n<code>{e}</code>")

    elif text.startswith("/status"):
        try:
            from storage import load_seen_tenders
            seen = load_seen_tenders()
            open_count = sum(1 for t in seen.values() if t.get("status") == "Open")
            _send_message(
                f"📊 <b>Stato attuale</b>\n\n"
                f"Gare tracciate: {len(seen)}\n"
                f"Ancora aperte: {open_count}"
            )
        except Exception as e:
            _send_message(f"❌ Errore:\n<code>{e}</code>")

    elif text.startswith("/start") or text.startswith("/help"):
        _send_message(
            "👋 <b>BEI Tender Agent</b>\n\n"
            "Comandi disponibili:\n"
            "/check — cerca nuove gare adesso\n"
            "/status — mostra quante gare sono tracciate"
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
            msg = update.get("message", {})
            # Accetta solo messaggi dal chat_id autorizzato
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
            pass  # Silenzia i log HTTP

    port = int(os.environ.get("PORT", 8080))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    # Avvia health server in background (necessario per Render)
    threading.Thread(target=run_health_server, daemon=True).start()
    run_bot()
