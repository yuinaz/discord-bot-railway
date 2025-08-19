silence_healthz_logs()

from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route
from satpambot.dashboard.webui import register_webui
import os
import time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_socketio import SocketIO
from dotenv import load_dotenv
import psutil

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "changeme")

socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

APP_START_TS = time.time()

def is_logged_in():
    return session.get("logged_in") is True

@app.context_processor
def inject_globals():
    return {
        "theme": os.getenv("THEME", "dark"),
        "dash_bg": os.getenv("DASH_BG_IMAGE", "/static/img/bg-login.jpg"),
        "cache_bust": int(APP_START_TS)
    }

@app.route("/")
def home():
    if not is_logged_in():
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        expected_user = os.getenv("ADMIN_USERNAME", "admin")
        expected_pass = os.getenv("ADMIN_PASSWORD", "admin123")
        uname = request.form.get("username", "")
        pwd = request.form.get("password", "")
        if uname == expected_user and pwd == expected_pass:
            session["logged_in"] = True
            session["username"] = uname
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Username / password salah.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))
    return render_template("dashboard.html")

@app.route("/metrics")
def metrics():
    cpu = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory()
    return jsonify({
        "cpu": cpu,
        "ram_mb": int(mem.used/1024/1024),
        "ram_total_mb": int(mem.total/1024/1024)
    })

@app.route("/uptime")
def uptime():
    seconds = int(time.time() - APP_START_TS)
    return jsonify({
        "uptime_seconds": seconds,
        "started_at": datetime.utcfromtimestamp(APP_START_TS).isoformat() + "Z"
    })

@app.route("/api/servers")
def api_servers():
    if not is_logged_in():
        return jsonify({"error": "unauthorized"}), 401
    return jsonify([
        {"name": "Gateway-01", "status": "online", "ping_ms": 12},
        {"name": "Bot-Core", "status": "online", "ping_ms": 28},
        {"name": "DB-Node", "status": "degraded", "ping_ms": 140}
    ])

DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "true").lower() == "true"
if DISCORD_ENABLED:
    try:
        from modules.discord_bot import run_bot, set_flask_app
        set_flask_app(app)
    except Exception as e:
        print(f"[WARN] Discord module not loaded: {e}")

@socketio.on("connect")
def on_connect():
    pass

@app.route("/start-bot")
def start_bot_route():
    if DISCORD_ENABLED:
        from modules.discord_bot import run_bot, bot_running
        if not bot_running():
            run_bot(background=True)
            return "Bot starting", 200
        else:
            return "Bot already running", 200
    return "Discord disabled", 200

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ## PATCH: app-root hotfix
# - perbaiki import discord bot (absolute package, fallback)
# - map template & static ke dashboard
# - tambahkan /healthz, /favicon.ico, /shutdown, dan 404 aman

try:
    import os as _os
    from flask import send_from_directory as _sfd, request as _req  # type: ignore
    from jinja2 import ChoiceLoader as _ChoiceLoader, FileSystemLoader as _FileSystemLoader, TemplateNotFound as _TemplateNotFound  # type: ignore

    # 1) template & static mapping
    _BASE_DIR = _os.path.dirname(__file__)
    _TPL_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "templates")
    _STA_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "static")
    if _os.path.isdir(_TPL_DIR):
        try:
            app.jinja_loader = _ChoiceLoader([app.jinja_loader, _FileSystemLoader(_TPL_DIR)])
        except Exception:
            app.jinja_env.loader = _ChoiceLoader([app.jinja_env.loader, _FileSystemLoader(_TPL_DIR)])
    if _os.path.isdir(_STA_DIR) and "static_custom" not in app.view_functions:
        app.add_url_rule("/static/<path:filename>", "static_custom", lambda filename: _sfd(_STA_DIR, filename))

    # 2) favicon route (hindari 404)
    if "favicon" not in app.view_functions:
        @app.get("/favicon.ico")
        def favicon():
            fn = _os.path.join(_STA_DIR, "favicon.ico")
            if _os.path.isfile(fn):
                return _sfd(_STA_DIR, "favicon.ico")
            return ("", 204)

    # 3) healthz (untuk uptime check)
    if "healthz" not in app.view_functions:
        @app.get("/healthz")
        def healthz():
            return "ok", 200

    # 4) safe 404 handler
    @app.errorhandler(404)
    def _patched_not_found(e):
        try:
            return render_template("404.html"), 404  # type: ignore[name-defined]
        except _TemplateNotFound:
            return "404 Not Found", 404

    # 5) /shutdown agar mudah stop di Windows dev server
    if "shutdown" not in app.view_functions:
        @app.post("/shutdown")
        def shutdown():
            func = _req.environ.get("werkzeug.server.shutdown")
            if func:
                func()
                return "shutting down...", 200
            return "server does not support shutdown", 501
except Exception as _e:
    pass

# Import helper bot (absolute package, fallback)
try:
    from satpambot.bot.modules.discord_bot import run_bot, bot_running  # type: ignore
except Exception:  # fallback legacy import path
    try:
        from modules.discord_bot import run_bot, bot_running  # type: ignore
    except Exception:
        def run_bot(*a, **kw): raise RuntimeError("Discord module not loaded (run_bot unavailable)")
        def bot_running(): return False

# ## PATCH: app-root hotfix (templates, favicon, healthz, 404 aman, shutdown, import run_bot)
try:
    import os as _os
    from flask import send_from_directory as _sfd, request as _req, render_template  # type: ignore
    from jinja2 import ChoiceLoader as _ChoiceLoader, FileSystemLoader as _FileSystemLoader, TemplateNotFound as _TemplateNotFound  # type: ignore

    # Map Jinja ke dashboard/templates
    _BASE_DIR = _os.path.dirname(__file__)
    _TPL_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "templates")
    _STA_DIR = _os.path.join(_BASE_DIR, "satpambot", "dashboard", "static")
    if _os.path.isdir(_TPL_DIR):
        try:
            app.jinja_loader = _ChoiceLoader([app.jinja_loader, _FileSystemLoader(_TPL_DIR)])
        except Exception:
            app.jinja_env.loader = _ChoiceLoader([app.jinja_env.loader, _FileSystemLoader(_TPL_DIR)])

    # Static (optional): arahkan /static ke dashboard/static bila belum ada
    if _os.path.isdir(_STA_DIR) and "static_custom" not in app.view_functions:
        app.add_url_rule("/static/<path:filename>", "static_custom", lambda filename: _sfd(_STA_DIR, filename))

    # Favicon agar tidak 404
    if "favicon" not in app.view_functions:
        @app.get("/favicon.ico")
        def favicon():
            fn = _os.path.join(_STA_DIR, "favicon.ico")
            if _os.path.isfile(fn):
                return _sfd(_STA_DIR, "favicon.ico")
            return ("", 204)

    # Healthcheck
    if "healthz" not in app.view_functions:
        @app.get("/healthz")
        def healthz():
            return "ok", 200

    # 404 aman (pakai template kalau ada; fallback teks jika tidak)
    @app.errorhandler(404)
    def _patched_not_found(e):
        try:
            return render_template("404.html"), 404
        except _TemplateNotFound:
            return "404 Not Found", 404

    # Endpoint shutdown (POST) untuk mematikan server dev di Windows
    if "shutdown" not in app.view_functions:
        @app.post("/shutdown")
        def shutdown():
            func = _req.environ.get("werkzeug.server.shutdown")
            if func:
                func()
                return "shutting down...", 200
            return "server does not support shutdown", 501
except Exception:
    pass

# Perbaiki import run_bot dengan fallback
try:
    from satpambot.bot.modules.discord_bot import run_bot, bot_running  # type: ignore
except Exception:
    try:
        from modules.discord_bot import run_bot, bot_running  # type: ignore
    except Exception:
        def run_bot(*a, **kw): raise RuntimeError("Discord module not loaded (run_bot unavailable)")
        def bot_running(): return False
# ## END PATCH



try:
    register_webui(app)
except Exception:
    pass

ensure_healthz_route(app)
