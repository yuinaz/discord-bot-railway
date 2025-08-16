# main.py
# -*- coding: utf-8 -*-
import os
import sys
import importlib
import asyncio
import threading
import logging
from typing import Optional

# =========================
# Logging
# =========================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("entry")


# =========================
# Utility
# =========================
def env_bool(name: str, default: Optional[bool] = None) -> Optional[bool]:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def should_run_bot() -> bool:
    """
    Default: JALAN kalau ada token (DISCORD_TOKEN/BOT_TOKEN).
    Bisa dipaksa OFF dengan RUN_BOT=0, atau ON dengan RUN_BOT=1.
    """
    forced = env_bool("RUN_BOT", None)
    if forced is not None:
        return forced
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    return bool(token)


def get_port() -> int:
    try:
        return int(os.getenv("PORT", "10000"))
    except Exception:
        return 10000


# =========================
# Dashboard (Flask) loader
# =========================
def load_dashboard_app():
    """
    Coba import dashboard utama: satpambot.dashboard.app
    Harus expose variabel 'app' (Flask instance).
    Kalau gagal, bikin mini-app fallback supaya Render tetap UP.
    """
    try:
        mod = importlib.import_module("satpambot.dashboard.app")
        app = getattr(mod, "app", None)
        if app is None:
            raise RuntimeError("satpambot.dashboard.app ditemukan, tapi tidak ada 'app'")
        log.info("✅ Dashboard app loaded: satpambot.dashboard.app")
        # Kurangi spam log GET /ping
        try:
            @app.before_request
            def _noisy_ping_filter():
                from flask import request
                if request.path == "/ping":
                    # Turunkan level ke DEBUG supaya gak banjiri log
                    logging.getLogger("werkzeug").setLevel(logging.WARNING)
        except Exception:
            pass
        return app
    except Exception as e:
        log.warning("app dashboard gagal diimport: %s; pakai mini fallback.", e)
        from flask import Flask, jsonify, redirect

        mini = Flask("mini-web")

        @mini.route("/ping")
        def _ping():
            return "ok"

        @mini.route("/healthz")
        def _healthz():
            return jsonify(ok=True)

        @mini.route("/")
        def _root():
            return redirect("/ping", code=302)

        return mini


def run_web(app):
    host = "0.0.0.0"
    port = get_port()
    log.info("🌐 Starting Flask on %s:%s", host, port)
    # Development server sudah cukup untuk Render; gunakan WSGI bila perlu.
    app.run(host=host, port=port, use_reloader=False)


# =========================
# Bot runner (thread)
# =========================
def _bot_thread_main():
    """
    Jalan di thread terpisah; aman untuk asyncio.run().
    Coba shim modern dulu, lalu fallback legacy bila ada.
    Tidak meledak jika modul tidak ada → web tetap hidup.
    """
    candidates = [
        # Rekomendasi (mono)
        ("satpambot.bot.modules.discord_bot.shim_runner", "start_bot"),
        # Fallback legacy (kalau masih ada)
        ("satpambot.bot.modules.discord_bot.discord_bot", "start_bot"),
        ("satpambot.bot.modules.discord_bot.discord_bot", "main"),
    ]
    last_err = None
    for mod_name, fn_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name, None)
            if fn is None:
                raise AttributeError(f"{mod_name} tidak punya fungsi {fn_name}")

            if asyncio.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
            log.info("🤖 Bot runner OK via %s.%s", mod_name, fn_name)
            return
        except Exception as e:
            last_err = e
            log.warning("Gagal start bot via %s.%s: %s", mod_name, fn_name, e)
    if last_err:
        log.error("Bot crash: %s", last_err)


def start_bot_background_if_needed():
    if not should_run_bot():
        log.info("🧪 RUN_BOT=0 atau token tidak tersedia → bot dimatikan.")
        return

    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        log.warning("ENV DISCORD_TOKEN / BOT_TOKEN tidak diset → bot tidak dijalankan.")
        return

    t = threading.Thread(target=_bot_thread_main, name="bot-thread", daemon=True)
    t.start()
    log.info("🚀 Bot thread started.")


# =========================
# Entry point
# =========================
def main():
    log.info(
        "ENTRY main.py start | RUN_BOT=%r | PORT=%s",
        os.getenv("RUN_BOT", ""),
        get_port(),
    )
    app = load_dashboard_app()
    # Jalankan bot di background bila memenuhi syarat
    start_bot_background_if_needed()
    # Jalankan web (blok sampai exit)
    run_web(app)


if __name__ == "__main__":
    # Pastikan project root ada di sys.path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        main()
    except KeyboardInterrupt:
        log.info("Shutdown requested by user.")
    except Exception as e:
        log.exception("Fatal error: %s", e)
        raise
