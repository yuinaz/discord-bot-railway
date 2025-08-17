import os
import logging
import asyncio
import threading

# -------------------------------------------------------------------
# Env loading (.env lalu .env.local override untuk lokal)
# -------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local", override=True)
except Exception:
    pass  # kalau python-dotenv belum terpasang, lanjut saja

# -------------------------------------------------------------------
# Auto-enable RUN_BOT jika token tersedia di env (tanpa export manual)
# Menerima beberapa nama variabel umum, dinormalisasi ke DISCORD_TOKEN
# -------------------------------------------------------------------
try:
    _token = None
    for _k in ("DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "BOT_TOKEN", "TOKEN", "TOKEN_BOT"):
        _v = os.getenv(_k)
        if _v and _v.strip():
            _token = _v.strip()
            os.environ["DISCORD_TOKEN"] = _token
            break

    _rb = (os.getenv("RUN_BOT", "auto").strip().lower())
    if (_token and _rb in ("auto", "", "0", "false", "off")) or _rb in ("1", "true", "yes", "on", "only"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass

# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()

# -------------------------------------------------------------------
# Mute akses log khusus /api/live (tanpa matikan log lain)
# -------------------------------------------------------------------
try:
    from werkzeug.serving import WSGIRequestHandler

    class _SilenceLive(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                m = record.getMessage()
            except Exception:
                return True
            return "/api/live" not in m

    for _name in ("werkzeug", "werkzeug.serving"):
        _lg = logging.getLogger(_name)
        _lg.addFilter(_SilenceLive())
        for _h in list(getattr(_lg, "handlers", []) or []):
            try:
                _h.addFilter(_SilenceLive())
            except Exception:
                pass

    _orig_log_request = WSGIRequestHandler.log_request

    def _log_request_sans_live(self, code="-", size="-"):
        line = getattr(self, "requestline", "") or ""
        if "/api/live" in line:
            return
        return _orig_log_request(self, code, size)

    WSGIRequestHandler.log_request = _log_request_sans_live
except Exception:
    pass

# -------------------------------------------------------------------
# Baca env final
# -------------------------------------------------------------------
RUN_BOT = os.getenv("RUN_BOT", "0")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

# -------------------------------------------------------------------
# Load Flask app (utama: satpambot.dashboard.app; fallback: app)
# -------------------------------------------------------------------
app = None
socketio = None
loaded_from = None

try:
    from satpambot.dashboard.app import app as _app  # type: ignore
    app = _app
    loaded_from = "satpambot.dashboard.app"
    try:
        from satpambot.dashboard.app import socketio as _socketio  # type: ignore
        socketio = _socketio
    except Exception:
        socketio = None
except Exception:
    try:
        from app import app as _app  # type: ignore
        app = _app
        loaded_from = "app"
        try:
            from app import socketio as _socketio  # type: ignore
            socketio = _socketio
        except Exception:
            socketio = None
    except Exception as e:
        log.exception("Gagal import dashboard app: %s", e)
        raise SystemExit(2)

# -------------------------------------------------------------------
# LOG urutan sesuai baseline
# -------------------------------------------------------------------
log.info("ENTRY main.py start | RUN_BOT='%s' | PORT=%s", RUN_BOT, PORT)
log.info("✅ Dashboard app loaded: %s", loaded_from)

# -------------------------------------------------------------------
# Runner bot di background thread (hanya jika token ada & RUN_BOT aktif)
# -------------------------------------------------------------------
def _start_bot_bg():
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
        return

    start = None
    try:
        # runner utama
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as start  # type: ignore
    except Exception:
        try:
            # fallback runner (kalau ada)
            from satpambot.bot.modules.discord_bot.shim_runner import start_bot as start  # type: ignore
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
            # beri jeda biar tidak tight loop
            await asyncio.sleep(5)

    try:
        asyncio.run(_run())
    except RuntimeError:
        # Jika sudah ada event loop (mis. di socketio), jalankan manual
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    if RUN_BOT.lower() in ("1", "true", "yes", "on", "only"):
        t = threading.Thread(target=_start_bot_bg, name="DiscordBotThread", daemon=True)
        t.start()
    else:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")

    log.info("🌐 Starting Flask on %s:%s", HOST, PORT)

    if app is None:
        raise SystemExit("Flask app not found")

    if socketio:
        # gunakan socketio jika tersedia
# === SILENCE /api/live,/ping ===
try:
    import logging
    from werkzeug.serving import WSGIRequestHandler
    SILENCE_PATHS = {"/api/live", "/ping", "/healthz", "/uptime"}

    class _SilencePaths(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            return not any(sp in m for sp in SILENCE_PATHS)

    # pasang filter ke logger werkzeug + handlers
    for name in ("werkzeug","werkzeug.serving"):
        lg = logging.getLogger(name)
        lg.addFilter(_SilencePaths())
        for h in list(getattr(lg, "handlers", []) or []):
            try: h.addFilter(_SilencePaths())
            except Exception: pass

    # patch handler agar akses ke path di atas tidak dicetak
    _orig_log_request = WSGIRequestHandler.log_request
    def _log_request_sans_paths(self, code='-', size='-'):
        line = getattr(self, "requestline", "") or ""
        if any(sp in line for sp in SILENCE_PATHS):
            return
        return _orig_log_request(self, code, size)
    WSGIRequestHandler.log_request = _log_request_sans_paths
except Exception:
    pass
# === END ===
        socketio.run(app, host=HOST, port=PORT, allow_unsafe_werkzeug=True)
    else:
        app.run(host=HOST, port=PORT)
