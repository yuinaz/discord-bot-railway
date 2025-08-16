
import os, logging, asyncio, threading

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL","INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

RUN_BOT = os.getenv("RUN_BOT","1")
HOST    = os.getenv("HOST","0.0.0.0")
PORT    = int(os.getenv("PORT","5000"))

log.info("ENTRY main.py start | RUN_BOT='%s' | PORT=%s", RUN_BOT, PORT)

app = None
socketio = None
loaded_from = None

try:
    from satpambot.dashboard.app import app as _app
    app = _app
    loaded_from = "satpambot.dashboard.app"
    try:
        from satpambot.dashboard.app import socketio as _socketio
        socketio = _socketio
    except Exception:
        socketio = None
except Exception:
    try:
        from app import app as _app
        app = _app
        loaded_from = "app"
        try:
            from app import socketio as _socketio
            socketio = _socketio
        except Exception:
            socketio = None
    except Exception as e:
        log.exception("Gagal import dashboard app: %s", e)
        raise SystemExit(2)

log.info("✅ Dashboard app loaded: %s", loaded_from)

def _start_bot_bg():
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
        return
    start = None
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as start
    except Exception:
        try:
            from satpambot.bot.modules.discord_bot.shim_runner import start_bot as start
        except Exception:
            start = None
    if not start:
        log.info("🧪 Runner bot tidak ditemukan → bot dimatikan.")
        return

    async def _run():
        try:
            await start()
        except Exception as e:
            log.exception("Bot crash: %s", e)
            await asyncio.sleep(5)

    try:
        asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

if __name__ == "__main__":
    if RUN_BOT in ("0","false","False"):
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
    else:
        t = threading.Thread(target=_start_bot_bg, name="DiscordBotThread", daemon=True)
        t.start()

    log.info("🌐 Starting Flask on %s:%s", HOST, PORT)
    if app is None:
        raise SystemExit("Flask app not found")
    if socketio:

# === SILENCE /api/live ===
try:
    import logging
    from werkzeug.serving import WSGIRequestHandler

    class _SilenceLive(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            return "/api/live" not in m

    # pasang filter di logger dan semua handler terkait
    for name in ("werkzeug", "werkzeug.serving"):
        lg = logging.getLogger(name)
        lg.addFilter(_SilenceLive())
        for h in list(getattr(lg, "handlers", []) or []):
            h.addFilter(_SilenceLive())

    # patch handler request agar tidak log baris yang mengandung /api/live
    _orig_log_request = WSGIRequestHandler.log_request
    def _log_request_sans_live(self, code='-', size='-'):
        line = getattr(self, "requestline", "") or ""
        if "/api/live" in line:
            return
        return _orig_log_request(self, code, size)
    WSGIRequestHandler.log_request = _log_request_sans_live
except Exception:
    pass
# === END ===

        socketio.run(app, host=HOST, port=PORT, allow_unsafe_werkzeug=True)
    else:
        app.run(host=HOST, port=PORT)
# === SILENCE API LIVE LOGS ===
try:
    import logging
    class _SilenceLive(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            return "/api/live" not in m
    logging.getLogger("werkzeug").addFilter(_SilenceLive())
except Exception:
    pass
# === END ===
