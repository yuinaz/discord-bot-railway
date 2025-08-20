
# main.py — single-process runner (Render free plan friendly)
from __future__ import annotations
import os, logging, threading, asyncio, time

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("main")

# Threading-only (Render free plan); no eventlet/gevent
os.environ.setdefault("SOCKETIO_ASYNC_MODE", os.getenv("SOCKETIO_ASYNC_MODE", "threading"))
os.environ.setdefault("DISABLE_EVENTLET", os.getenv("DISABLE_EVENTLET", "1"))

# Resolve Flask app from app.py
from app import app as flask_app, create_app as _create_app

app = flask_app or (_create_app() if callable(_create_app) else None)
if app is None:
    raise RuntimeError("Failed to resolve Flask app (app is None)")

# Start time after app exists (fix AttributeError)
app.config["START_TIME"] = time.time()

def _bot_runner():
    try:
        from satpambot.bot.modules.discord_bot.shim_runner import start_bot
    except Exception as e:
        log.error("Bot runner not found: %s", e); return
    try:
        asyncio.run(start_bot())
    except Exception as e:
        log.error("Bot exited with error: %s", e)

RUN_BOT = os.getenv("RUN_BOT", "1").lower() in ("1","true","yes","on")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "10000"))

if __name__ == "__main__":
    if RUN_BOT:
        threading.Thread(target=_bot_runner, name="DiscordBotThread", daemon=True).start()
        log.info("🤖 Bot started in background thread.")
    log.info("🌐 Serving web on %s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
