# main.py — single service (web + discord bot), Render-friendly
from __future__ import annotations
import os, logging, threading

logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("entry")

os.environ.setdefault("SOCKETIO_ASYNC_MODE", os.getenv("SOCKETIO_ASYNC_MODE","threading"))
os.environ.setdefault("DISABLE_EVENTLET", os.getenv("DISABLE_EVENTLET","1"))
os.environ.setdefault("TZ", os.getenv("TZ","Asia/Jakarta"))

# Flask app (fail-fast)
from app import create_app
app = create_app()

# Optional: background Discord bot
def _bot_runner():
    try:
        from satpambot.bot.main import start_bot_background
        start_bot_background()
        log.info("🤖 Bot started in background thread.")
    except Exception as e:
        log.warning("Bot not started: %s", e, exc_info=True)

if os.getenv("RUN_BOT", "1").lower() in ("1","true","yes","on"):
    threading.Thread(target=_bot_runner, name="DiscordBotThread", daemon=True).start()

if __name__ == "__main__":
    host = os.getenv("HOST","0.0.0.0"); port = int(os.getenv("PORT","10000"))
    # SocketIO (optional)
    try:
        from app import socketio  # type: ignore
    except Exception:
        socketio = None
    log.info("🌐 Serving web on %s:%s", host, port)
    if socketio:
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port, debug=False, use_reloader=False)
