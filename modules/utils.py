
import threading
import datetime
import os
import time
import requests
import psutil
import discord
from functools import wraps
from flask import Flask, render_template, redirect, session, request, jsonify

# === Flask App ===
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")
app.permanent_session_lifetime = datetime.timedelta(minutes=30)

NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")
START_TIME = datetime.datetime.now()

# === Login Required Decorator ===
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated

# === Jalankan backup settings saat startup ===
try:
    from modules.backup import backup_settings
    backup_settings()
except Exception as e:
    print(f"❌ Gagal memanggil backup_settings(): {e}")

# === Routes Dasar & Dashboard ===
@app.route("/ping")
def ping():
    return "✅ Bot is alive!", 200

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    ram = psutil.virtual_memory().used // (1024 * 1024)
    cpu = psutil.cpu_percent()
    uptime = datetime.datetime.now() - START_TIME
    return render_template("dashboard.html", uptime=str(uptime).split('.')[0], ram_usage=ram, cpu_usage=cpu)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    settings = load_settings()
    if request.method == "POST":
        settings["AUTO_BAN_ENABLED"] = request.form.get("autoban") == "on"
        settings["ADMIN_IDS"] = [x.strip() for x in request.form.get("adminIds", "").split(",") if x.strip()]
        settings["NOTIFY_WEBHOOK"] = request.form.get("webhook", "")
        save_settings(settings)
        return redirect("/settings")
    return render_template("settings.html", settings=settings)

@app.route("/config")
def config_redirect():
    return redirect("/settings")

@app.route("/grafik")
@login_required
def grafik():
    return render_template("grafik.html")

@app.route("/profil")
@login_required
def profil():
    return render_template("profil.html", user=session.get("user"))

@app.route("/api/stats")
def stats_api():
    uptime = datetime.datetime.now() - START_TIME
    settings = load_settings()
    return jsonify({
        "uptime": str(uptime).split('.')[0],
        "phishing_count": app.config.get("phishing_count", 0),
        "messages_checked": app.config.get("messages_checked", 0),
        "autoban_enabled": settings.get("AUTO_BAN_ENABLED", False)
    })

@app.route("/api/server_stats")
def api_server_stats():
    from modules.discord_bot import bot
    return jsonify({g.name: g.member_count for g in bot.guilds})

@app.route("/api/server_resource")
def server_resource():
    return jsonify({
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent
    })

@app.route("/api/guild_members")
def guild_members():
    from modules.discord_bot import bot
    return jsonify({
        guild.name: len([
            m for m in guild.members 
            if not m.bot and m.status != discord.Status.offline
        ]) for guild in bot.guilds
    })

# === Settings Management ===
def load_settings():
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    try:
        with open("settings.json", "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print("❌ Gagal menyimpan settings.json:", e)

# === Flask & Heartbeat Thread ===
def run_flask():
    port_str = os.environ.get("PORT")
    try:
        port = int(port_str) if port_str and port_str.isdigit() else 8080
    except Exception as e:
        print("❌ Gagal membaca PORT:", e)
        port = 8080

    print(f"🌐 Menjalankan Flask di http://0.0.0.0:{port}")
    print("✅ Flask route aktif. Silakan akses endpoint /dashboard atau /ping.")
    app.run(host='0.0.0.0', port=port)

def heartbeat_loop():
    while True:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❤️ Heartbeat: bot masih hidup.")
        time.sleep(600)

def keep_alive():
    try:
        threading.Thread(target=run_flask, daemon=True).start()
        threading.Thread(target=heartbeat_loop, daemon=True).start()
    except Exception as e:
        print("❌ Gagal menjalankan keep_alive():", e)

# === Crash Reporter ===
def notify_crash():
    if NOTIFY_WEBHOOK:
        try:
            requests.post(NOTIFY_WEBHOOK, json={"content": "❌ Bot Satpam mati/crash! Mohon segera cek server."})
            print("📡 Notifikasi crash terkirim.")
        except Exception as e:
            print("❌ Gagal mengirim notifikasi crash:", e)
    else:
        print("⚠️ Webhook untuk notifikasi crash belum diatur.")

# === Log saat startup
def log_startup():
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 🚀 SatpamBot berhasil dijalankan.")
