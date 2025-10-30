#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import logging
import threading
import asyncio
from pathlib import Path

# Load local .env file if present. Prefer python-dotenv when available; fall back
# to a simple parser so running `main.py` locally with a .env works without extra
# setup. We avoid printing any secret values.
try:
    from dotenv import load_dotenv  # type: ignore

    dotenv_path = Path(".env")
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    # Fallback: naive .env loader (KEY=VALUE lines, ignores comments/blank)
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        try:
            for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # Remove surrounding quotes if present
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                # Only set env var if not already present in the environment
                if os.getenv(k) is None:
                    os.environ[k] = v
        except Exception:
            # If anything goes wrong, proceed without halting; main will validate required envs
            pass

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

    # --- shim_runner import (minimal, non-breaking) ---
    try:
        from satpambot.bot.modules.discord_bot import shim_runner           # prefer canonical
    except Exception:
        try:
            import satpambot.bot.shim_runner as shim_runner  # fallback 1
        except Exception:
            import satpambot.shim_runner as shim_runner      # fallback 2
    # --- end shim_runner import ---
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

    
    # --- file logging to run_YYYYmmdd_HHMMSS.log ---
    import time, logging.handlers, os
# --- shim_runner import (top-level, minimal) ---
try:
    from satpambot.bot.modules.discord_bot import shim_runner           # canonical
except Exception:
    try:
        import satpambot.bot.shim_runner as shim_runner  # fallback 1
    except Exception:
        import satpambot.shim_runner as shim_runner      # fallback 2
# --- end shim_runner import ---
    _ts = time.strftime("%Y%m%d_%H%M%S")
    _log_name = f"run_{_ts}.log"
    _root = logging.getLogger()
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in _root.handlers):
        _fh = logging.handlers.RotatingFileHandler(
            _log_name, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        _fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        _root.addHandler(_fh)
        if _root.level > logging.INFO:
            _root.setLevel(logging.INFO)
        logging.getLogger("entry.main").info("📄 file log => %s", os.path.abspath(_log_name))
    # --- end file logging ---
asyncio.run(shim_runner.start_bot())

if __name__ == "__main__":
    main()
