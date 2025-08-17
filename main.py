import os
import logging
import asyncio
import threading

# =========================
# Env loading (.env + .env.local override)
# =========================
try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(".env.local", override=True)
except Exception:
    pass  # kalau python-dotenv tidak ada, lanjut

# =========================
# Auto-enable RUN_BOT jika ada token (normalize ke DISCORD_TOKEN)
# =========================
try:
    token = None
    for key in ("DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "BOT_TOKEN", "TOKEN", "TOKEN_BOT"):
        val = os.getenv(key)
        if val and val.strip():
            token = val.strip()
            os.environ["DISCORD_TOKEN"] = token  # normalisasi nama
            break
    rb = (os.getenv("RUN_BOT", "auto").strip().lower())
    if (token and rb in ("auto", "", "0", "false", "off")) or rb in ("1", "true", "yes", "on", "only"):
        os.environ["RUN_BOT"] = "1"
except Exception:
    pass

# =========================
# Logging setup
# =========================
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger()

# =========================
# Silence akses log untuk path ringan (tanpa matikan log lain)
# =========================
try:
    from werkzeug.serving import WSGIRequestHandler

    SILENCE_PATHS = {"/api/live", "/ping", "/healthz", "/uptime"}

    class _SilencePaths(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage()
            except Exception:
                return True
            return not any(p in msg for p in SILENCE_PATHS)

    for name in ("werkzeug", "werkzeug.serving"):
        lg = logging.getLogger(name)
        lg.addFilter(_SilencePaths())
        for h in list(getattr(lg, "handlers", []) or []):
            try:
                h.addFilter(_SilencePaths())
            except Exception:
                pass

    _orig_log_request = WSGIRequestHandler.log_request

    def _log_request_sans_paths(self, code="-", size="-"):
        line = getattr(self, "requestline", "") or ""
        if any(p in line for p in SILENCE_PATHS):
            return
        return _orig_log_request(self, code, size)

    WSGIRequestHandler.log_request = _log_request_sans_paths
except Exception:
    pass

# =========================
# Konfigurasi dasar
# =========================
RUN_BOT = os.getenv("RUN_BOT", "0")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("RENDER_PORT", "8080")))

# =========================
# Import Flask app (utama: satpambot.dashboard.app; fallback: app)
# =========================
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

# =========================
# Log startup baseline
# =========================
log.info("ENTRY main.py start | RUN_BOT='%s' | PORT=%s", RUN_BOT, PORT)
log.info("✅ Dashboard app loaded: %s", loaded_from)

# =========================
# Bot runner di background thread (jika aktif)
# =========================
def _start_bot_bg():
    tkn = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not tkn:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
        return

    # cari runner
    start = None
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as start  # type: ignore
    except Exception:
        try:
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
            await asyncio.sleep(5)

    try:
        asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

# =========================
# Main
# =========================
if __name__ == "__main__":
    if RUN_BOT.lower() in ("1", "true", "yes", "on", "only"):
        th = threading.Thread(target=_start_bot_bg, name="DiscordBotThread", daemon=True)
        th.start()
    else:
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")

    log.info("🌐 Starting Flask on %s:%s", HOST, PORT)

    if app is None:
        raise SystemExit("Flask app not found")

    if socketio:
        # Render pakai Werkzeug; allow_unsafe supaya tidak error di prod dev-server
        socketio.run(app, host=HOST, port=PORT, allow_unsafe_werkzeug=True)
    else:
        app.run(host=HOST, port=PORT)
