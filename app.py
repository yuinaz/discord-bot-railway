# app.py — Root Flask app (lengkap) yang:
# - memetakan template/static ke satpambot/dashboard/*
# - menambah /healthz, /metrics, /uptime, /favicon.ico, 404 aman, /shutdown
# - menyediakan /start-bot untuk menyalakan bot
# - mendeteksi dashboard app & bot runner secara fleksibel (termasuk app_dashboard)

import os
import time
import threading
import inspect
import asyncio
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
try:
    # Jika ada SocketIO di dashboard, nanti kita re-bind ke sini
    from flask_socketio import SocketIO
except Exception:
    SocketIO = None  # type: ignore

from jinja2 import ChoiceLoader, FileSystemLoader, TemplateNotFound
# quiet access log for /healthz and ensure route
from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route

# =========================
# Env loading (.env + .env.local)
# =========================
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=True))  # .env dari CWD ke atas
    local = Path(__file__).with_name(".env.local")
    if local.exists():
        load_dotenv(local, override=True)    # prioritas .env.local
except Exception:
    pass

# =========================
# Coba import dashboard app yang "asli", lalu patch di sini
# =========================
def _import_dashboard_app():
    """
    Deteksi modul dashboard dari beberapa kemungkinan lokasi/penamaan:
      - satpambot.dashboard.app_dashboard
      - satpambot.dashboard.app
      - dashboard.app_dashboard
      - dashboard.app
    Kalau semua gagal -> mini web.
    """
    candidates = [
        "satpambot.dashboard.app_dashboard",
        "satpambot.dashboard.app",
        "dashboard.app_dashboard",
        "dashboard.app",
    ]
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["app", "socketio"])
            app = getattr(m, "app")
            socketio = getattr(m, "socketio", None)
            return app, socketio
        except Exception:
            continue

    # fallback kalau tidak ada dashboard sama sekali: bikin mini-app
    mini = Flask("mini-web")

    @mini.get("/login")
    def _login_stub():
        return "Dashboard tidak tersedia (mini web).", 503

    return mini, None

app, socketio = _import_dashboard_app()

# silence werkzeug access logs for /healthz (/favicon.ico too)
silence_healthz_logs()

# Secret key (kompatibel nama env lama/baru)
app.secret_key = os.getenv("FLASK_SECRET") or os.getenv("SECRET_KEY", "changeme")
APP_START_TS = time.time()

# =========================
# Template & static mapping ke dashboard/*
# (ditambahkan/diduplikasi aman; tidak meledak jika sudah ada)
# =========================
_BASE_DIR = os.path.dirname(__file__)
_TPL_DIR = os.path.join(_BASE_DIR, "satpambot", "dashboard", "templates")
_STA_DIR = os.path.join(_BASE_DIR, "satpambot", "dashboard", "static")

if os.path.isdir(_TPL_DIR):
    try:
        app.jinja_loader = ChoiceLoader([app.jinja_loader, FileSystemLoader(_TPL_DIR)])
    except Exception:
        app.jinja_env.loader = ChoiceLoader([app.jinja_env.loader, FileSystemLoader(_TPL_DIR)])

if os.path.isdir(_STA_DIR) and "static_custom" not in app.view_functions:
    app.add_url_rule("/static/<path:filename>", "static_custom", lambda filename: send_from_directory(_STA_DIR, filename))

# =========================
# Context globals (opsional)
# =========================
@app.context_processor
def inject_globals():
    return {
        "theme": os.getenv("THEME", "dark"),
        "dash_bg": os.getenv("DASH_BG_IMAGE", "/static/img/bg-login.jpg"),
        "cache_bust": int(APP_START_TS),
    }

# =========================
# Routes minimum (jaga jika dashboard tidak punya root/login)
# =========================
def _has_route(rule: str) -> bool:
    return any(r.rule == rule for r in app.url_map.iter_rules())

if not _has_route("/"):
    @app.get("/")
    def _root():
        return redirect(url_for("login")) if _has_route("/login") else ("OK", 200)

if not _has_route("/login"):
    @app.get("/login")
    def _login_fallback():
        return "Login page not provided by dashboard.", 200

# =========================
# Ops/health routes untuk UptimeRobot/Render
# make sure /healthz exists (idempotent)
ensure_healthz_route(app)
# =========================
if not _has_route("/healthz"):
    @app.get("/healthz")
    def healthz():
        return "ok", 200

if not _has_route("/uptime"):
    @app.get("/uptime")
    def uptime():
        seconds = int(time.time() - APP_START_TS)
        return jsonify({
            "uptime_seconds": seconds,
            "started_at": datetime.utcfromtimestamp(APP_START_TS).isoformat() + "Z"
        })

if not _has_route("/metrics"):
    @app.get("/metrics")
    def metrics():
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.05)
            mem = psutil.virtual_memory()
            return jsonify({
                "cpu": cpu,
                "ram_mb": int(mem.used/1024/1024),
                "ram_total_mb": int(mem.total/1024/1024)
            })
        except Exception:
            return jsonify({"cpu": None, "ram_mb": None, "ram_total_mb": None})

if not _has_route("/favicon.ico"):
    @app.get("/favicon.ico")
    def favicon():
        fn = os.path.join(_STA_DIR, "favicon.ico")
        if os.path.isfile(fn):
            return send_from_directory(_STA_DIR, "favicon.ico")
        return ("", 204)

@app.errorhandler(404)
def not_found(e):
    try:
        return render_template("404.html"), 404
    except TemplateNotFound:
        return "404 Not Found", 404

# Matikan server dev (Windows) jika Ctrl+C ngeyel
if not _has_route("/shutdown"):
    @app.post("/shutdown")
    def shutdown():
        func = request.environ.get("werkzeug.server.shutdown")
        if func:
            func()
            return "shutting down...", 200
        return "server does not support shutdown", 501

# =========================
# Discord bot runner (tanpa event loop ganda)
# =========================
def _import_start_run():
    """Kembalikan tuple (start_bot, run_bot) jika tersedia (boleh None)."""
    start_bot = run_bot = None
    # prioritas package penuh dulu
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as _s  # type: ignore
        start_bot = _s
    except Exception:
        pass
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import run_bot as _r  # type: ignore
        run_bot = _r
    except Exception:
        pass
    # fallback import lama
    if start_bot is None:
        try:
            from modules.discord_bot.discord_bot import start_bot as _s2  # type: ignore
            start_bot = _s2
        except Exception:
            pass
    if run_bot is None:
        try:
            from modules.discord_bot.discord_bot import run_bot as _r2  # type: ignore
            run_bot = _r2
        except Exception:
            pass
    return start_bot, run_bot

def _start_bot_now():
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        return
    start_bot, run_bot = _import_start_run()

    # Bila start_bot coroutine → jalankan di event loop BARU (bukan asyncio.run di loop aktif)
    if start_bot and inspect.iscoroutinefunction(start_bot):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(start_bot())
        finally:
            loop.close()
        return

    # Bila run_bot sinkron (biasanya memanggil asyncio.run di dalamnya) → cukup panggil langsung
    if run_bot:
        try:
            run_bot()
        except TypeError:
            try:
                run_bot(background=True)
            except Exception:
                run_bot()

if not _has_route("/start-bot"):
    @app.get("/start-bot")
    def start_bot_route():
        token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
        if not token:
            return "Token tidak tersedia. Set DISCORD_TOKEN di .env/.env.local", 400
        threading.Thread(target=_start_bot_now, name="DiscordBotThread", daemon=True).start()
        return "Bot starting", 200

# =========================
# SocketIO guard (biar tak meledak bila dashboard tak pakai SocketIO)
# =========================
if socketio is None and SocketIO is not None:
    # Buat instance kosong (threading) agar main.py bisa .run() lewat socketio
    socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
