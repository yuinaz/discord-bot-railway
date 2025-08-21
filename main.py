# main.py — ENTRY SERVICE (run Flask + start bot bg)
from __future__ import annotations
import logging, os, threading, asyncio
from werkzeug.serving import WSGIRequestHandler

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("entry.main")

try:
    from app import create_app
    app = create_app()
    log.info("[web] Flask app created via create_app()")
except Exception:
    from flask import Flask
    app = Flask("satpambot_dashboard_fallback")
    @app.get("/healthz")
    def _healthz(): return "OK", 200
    @app.get("/")
    def _root(): return "SatpamBot dashboard fallback", 200
    @app.get("/uptime")
    def _uptime(): return "OK", 200
    log.warning("[app] fallback Flask app created")

def _run_asyncmaybe(fn):
    if asyncio.iscoroutinefunction(fn):
        asyncio.run(fn())
    else:
        fn()

def start_bot_background():
    def _target():
        try:
            from satpambot.bot.main import start_bot as _start
        except Exception:
            try:
                from satpambot.bot.main import main as _start
            except Exception:
                log.warning("Bot not started: start function not found in satpambot.bot.main")
                return
        try:
            log.info("🤖 Bot started in background thread using satpambot.bot.main.%s", _start.__name__)
            _run_asyncmaybe(_start)
        except Exception:
            log.exception("Bot thread crashed")
    threading.Thread(target=_target, name="satpambot-bg", daemon=True).start()

if os.getenv("DISABLE_BOT_RUN", "0") != "1":
    start_bot_background()

class _HealthzFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthz" not in str(getattr(record, "msg", ""))
logging.getLogger("werkzeug").addFilter(_HealthzFilter())

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    log.info("🌐 Serving web on 0.0.0.0:%s", port)
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host="0.0.0.0", port=port, debug=False)
