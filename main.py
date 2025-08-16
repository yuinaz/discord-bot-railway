import os, logging
from dotenv import load_dotenv

# .env utama lalu .env.local override untuk lokal
load_dotenv()
load_dotenv('.env.local', override=True)

# === AUTO RUN_BOT based on token from .env/.env.local ===
try:
    token = None
    for key in ("DISCORD_TOKEN","DISCORD_BOT_TOKEN","BOT_TOKEN","TOKEN","TOKEN_BOT"):
        val = os.getenv(key)
        if val and val.strip():
            token = val.strip()
            os.environ["DISCORD_TOKEN"] = token  # normalisasi nama
            break
    run_bot = (os.getenv("RUN_BOT","auto").strip().lower())
    if token and run_bot in ("auto","","0","false","off"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass
# === END ===

# === SILENCE /api/live ===
try:
    from werkzeug.serving import WSGIRequestHandler
    class _SilenceLive(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            return "/api/live" not in m
    # filter di logger werkzeug
    for name in ("werkzeug","werkzeug.serving"):
        lg = logging.getLogger(name)
        lg.addFilter(_SilenceLive())
        for h in list(getattr(lg, "handlers", []) or []):
            try: h.addFilter(_SilenceLive())
            except Exception: pass
    # patch handler agar baris akses /api/live tidak tercetak
    _orig_log_request = WSGIRequestHandler.log_request
    def _log_request_sans_live(self, code='-', size='-'):
        line = getattr(self, "requestline", "") or ""
        if "/api/live" in line: return
        return _orig_log_request(self, code, size)
    WSGIRequestHandler.log_request = _log_request_sans_live
except Exception:
    pass
# === END ===

import os, logging, asyncio, threading

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL","INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()

try:

import os, logging, asyncio, threading

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL","INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()

try:

# === AUTO RUN_BOT based on token from .env/.env.local ===
try:
    import os
    token = None
    for key in ("DISCORD_TOKEN","DISCORD_BOT_TOKEN","BOT_TOKEN","TOKEN","TOKEN_BOT"):
        val = os.getenv(key)
        if val and val.strip():
            token = val.strip()
            os.environ["DISCORD_TOKEN"] = token  # normalize
            break
    run_bot = (os.getenv("RUN_BOT","auto").strip().lower())
    if token and run_bot in ("auto","","0","false","off"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass
# === END AUTO ===

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

# === AUTO RUN_BOT based on token from .env/.env.local ===
try:
    import os
    token = None
    for key in ("DISCORD_TOKEN","DISCORD_BOT_TOKEN","BOT_TOKEN","TOKEN","TOKEN_BOT"):
        val = os.getenv(key)
        if val and val.strip():
            token = val.strip()
            os.environ["DISCORD_TOKEN"] = token  # normalize
            break
    run_bot = (os.getenv("RUN_BOT","auto").strip().lower())
    if token and run_bot in ("auto","","0","false","off"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass
# === END AUTO ===

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
