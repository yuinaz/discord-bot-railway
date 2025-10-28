#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import logging
import threading
import asyncio

# ------------------------------------------------------------------
# Logging config — keep the format the user expects:
# "INFO:entry.main:..."
# ------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("entry.main")

# Import Flask app from your existing app.py (Flask app variable must be named `app`)
from app import app  # noqa: E402

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "10000")))
WEB_THREADS = int(os.getenv("WEB_THREADS", "8"))
WEB_LOG_LEVEL = os.getenv("WEB_LOG_LEVEL", "WARNING").upper()

def _serve_web():
    """
    Serve the Flask app without the noisy Flask dev banner.
    Try waitress first (quiet), fallback to wsgiref (also quiet).
    Runs in a dedicated background thread.
    """
    # Prefer waitress (production-friendly, quiet)
    try:
        from waitress import serve as waitress_serve  # type: ignore
        logging.getLogger("waitress").setLevel(getattr(logging, WEB_LOG_LEVEL, logging.WARNING))
        waitress_serve(app, host=HOST, port=PORT, threads=WEB_THREADS)
        return
    except Exception:
        # Fallback: built-in wsgiref (quiet)
        from wsgiref.simple_server import make_server, WSGIRequestHandler

        class QuietHandler(WSGIRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                if self.path == "/healthz":
                    pass
                else:
                    super().log_message(format, *args)

        httpd = make_server(HOST, PORT, app, handler_class=QuietHandler)
        httpd.serve_forever()

def main():

    # --- Render Free preflight (non-fatal) ---
    try:
        import importlib
        _pre = importlib.import_module("scripts.preflight_render_free")
        _pre.main()
    except Exception as _e:
        logging.getLogger("entry.main").warning("[preflight] WARN: %r", _e)
    # Start web (unless disabled)
    if os.getenv("RUN_WEB", "1") != "0":
        log.info(f"🌐 Serving web on {HOST}:{PORT}")
        t = threading.Thread(target=_serve_web, name="web", daemon=True)
        t.start()
        log.info(f"Web is ready on port {PORT}")
    else:
        log.info("🌐 Web disabled by RUN_WEB=0")

    # Then start the Discord bot as usual
    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
    from satpambot.bot.modules.discord_bot import shim_runner
    asyncio.run(shim_runner.start_bot())

if __name__ == "__main__":
    main()
