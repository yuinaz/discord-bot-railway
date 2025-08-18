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
