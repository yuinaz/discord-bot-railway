# main.py — Entrypoint stabil untuk lokal & Render
# - Load .env / .env.prod / .env.local (prioritas .env.local)
# - Start Flask (atau SocketIO) tanpa reloader (Ctrl+C aman)
# - Start bot di background jika token ada (tanpa event loop ganda)

import os
import logging
import threading
import signal
import sys
import inspect
import asyncio
from pathlib import Path

# =========================
# Env loading berlapis
# =========================
try:
    from dotenv import load_dotenv
    ROOT = Path(__file__).resolve().parent

    f = ROOT / ".env"
    if f.exists():
        load_dotenv(f, override=False)

    if (os.getenv("ENV") or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "").lower().startswith("prod"):
        pf = ROOT / ".env.prod"
        if pf.exists():
            load_dotenv(pf, override=True)

    lf = ROOT / ".env.local"
    if lf.exists():
        load_dotenv(lf, override=True)
except Exception:
    pass

# Normalisasi token + RUN_BOT
try:
    token = None
    for key in ("DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "BOT_TOKEN", "TOKEN", "TOKEN_BOT"):
        v = os.getenv(key)
        if v and v.strip():
            token = v.strip()
            os.environ["DISCORD_TOKEN"] = token  # normalisasi
            break
    rb = (os.getenv("RUN_BOT") or "").strip().lower()
    if token and rb in ("", "0", "false", "off"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass

# =========================
# Logging
# =========================
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("entry")

# =========================
# Import Flask app (dengan socketio jika ada)
# =========================
from app import app as app  # type: ignore
try:
    from app import socketio as socketio  # type: ignore
except Exception:
    socketio = None

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("RENDER_PORT", "8080")))
RUN_BOT = os.getenv("RUN_BOT", "0")

log.info("ENTRY main.py start | RUN_BOT='%s' | PORT=%s", RUN_BOT, PORT)
log.info("✅ Dashboard app loaded: app")

# =========================
# Signal handler -> Ctrl+C aman
# =========================
def _sigint(signum, frame):
    print("\n^C received, shutting down...", flush=True)
    try:
        if socketio:
            try:
                socketio.stop()
            except Exception:
                pass
    finally:
        os._exit(0)

try:
    signal.signal(signal.SIGINT, _sigint)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _sigint)
except Exception:
    pass

# =========================
# Bot background starter (tanpa event loop ganda)
# =========================
def _import_start_run():
    start_bot = run_bot = None
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as _s  # type: ignore
        start_bot = _s
    except Exception:
        pass
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import run_bot as _r  # type: ignore
        run_bot = _r
    except Exception:
        pass
    if start_bot is None:
        try:
            from modules.discord_bot.discord_bot import start_bot as _s2  # type: ignore
            start_bot = _s2
        except Exception:
            pass
    if run_bot is None:
        try:
            from modules.discord_bot.discord_bot import run_bot as _r2  # type: ignore
            run_bot = _r2
        except Exception:
            pass
    return start_bot, run_bot

def _start_bot_bg():
    tkn = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not tkn:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
        return
    start_bot, run_bot = _import_start_run()
    try:
        if start_bot and inspect.iscoroutinefunction(start_bot):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(start_bot())
            finally:
                loop.close()
            return
        if run_bot:
            try:
                run_bot()
            except TypeError:
                try:
                    run_bot(background=True)
                except Exception:
                    run_bot()
            return
        log.info("🧪 Runner bot tidak ditemukan → bot dimatikan.")
    except Exception as e:
        log.exception("Bot crash: %s", e)

# =========================
# Main
# =========================
if __name__ == "__main__":
    if RUN_BOT.lower() in ("1", "true", "yes", "on", "only"):
        threading.Thread(target=_start_bot_bg, name="DiscordBotThread", daemon=True).start()
        log.info("🤖 Bot supervisor started in background")
    else:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")

    log.info("🌐 Starting Flask on %s:%s", HOST, PORT)

    # Jalankan tanpa reloader (Ctrl+C aman). Jika ada socketio, pakai itu.
    if socketio:
        socketio.run(app, host=HOST, port=PORT, allow_unsafe_werkzeug=True, debug=False, use_reloader=False)
    else:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
