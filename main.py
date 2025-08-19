# main.py — free-plan single service: web + discord bot
import os, logging, threading, asyncio, time
from time import sleep

logging.basicConfig(level=os.environ.get("LOG_LEVEL","INFO"), format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("entry")

os.environ.setdefault("SOCKETIO_ASYNC_MODE", os.getenv("SOCKETIO_ASYNC_MODE","threading"))
os.environ.setdefault("DISABLE_EVENTLET", os.getenv("DISABLE_EVENTLET","1"))

# Import Flask app/socketio from app.py
from app import app
try:
    from app import socketio
except Exception:
    socketio = None

app.config["START_TIME"] = time.time()

def _bot_runner():
    try:
        from satpambot.bot.modules.discord_bot.shim_runner import start_bot
    except Exception as e:
        log.error("Bot runner tidak ditemukan: %s", e)
        return
    try:
        asyncio.run(start_bot())
    except Exception as e:
        log.error("Bot berhenti dengan error: %s", e)

RUN_BOT = os.getenv("RUN_BOT", "1").lower() in ("1","true","yes","on")
HOST = os.getenv("HOST","0.0.0.0"); PORT = int(os.getenv("PORT","10000"))

if __name__ == "__main__":
    if RUN_BOT:
        threading.Thread(target=_bot_runner, name="DiscordBotThread", daemon=True).start()
        log.info("🤖 Bot started in background thread.")
    log.info("🌐 Serving web on %s:%s", HOST, PORT)
    if socketio:
        socketio.run(app, host=HOST, port=PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
