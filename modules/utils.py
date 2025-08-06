from flask import Blueprint, request, jsonify
import threading
import datetime
import os
import time
import requests
import psutil
import json

utils_bp = Blueprint("utils", __name__)

# 🔐 Webhook Notifikasi
NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")

# ⏱️ Start Time untuk uptime
from datetime import datetime
START_TIME = datetime.utcnow()

# === Global Cache untuk CPU Usage ===
CPU_USAGE = 0.0

def update_cpu_usage():
    global CPU_USAGE
    while True:
        CPU_USAGE = psutil.cpu_percent(interval=1)
        time.sleep(5)

# === Logging Aman ===
def safe_log(msg):
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}")

# === ROUTE: Ping ===
@utils_bp.route("/ping")
def ping():
    return "✅ Bot is alive!", 200

# === ROUTE: Info Uptime Bot ===
@utils_bp.route("/uptime")
def uptime():
    return jsonify({
        "uptime": get_uptime(),
        "ram_usage_mb": get_ram_usage(),
        "cpu_usage_percent": get_cpu_usage(),
    })

# === ROUTE: Statistik Lengkap (uptime + cpu + ram)
@utils_bp.route("/stats")
def stats():
    return jsonify({
        "uptime": get_uptime(),
        "ram_usage_mb": get_ram_usage(),
        "cpu_usage_percent": get_cpu_usage(),
        "status": "online"
    })

# === ROUTE: Health Check untuk monitoring (UptimeRobot, dll)
@utils_bp.route("/healthz")
def health():
    return jsonify({"status": "ok", "uptime": get_uptime()})

# === ROUTE: Ganti & Ambil Tema Aktif (POST / GET)
@utils_bp.route("/theme", methods=["GET", "POST"])
def theme():
    if request.method == "POST":
        try:
            data = request.get_json()
            theme = data.get("theme")
            if theme:
                set_theme(theme)
                return jsonify({"status": "success", "theme": theme})
            else:
                return jsonify({"status": "error", "message": "Tema tidak valid"}), 400
        except Exception as e:
            safe_log(f"❌ Gagal mengatur tema: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    # GET - ambil tema aktif sekarang
    try:
        theme_url = get_current_theme()
        theme_name = theme_url.split("/")[-1]
        return jsonify({"status": "success", "theme": theme_name, "url": theme_url})
    except Exception as e:
        safe_log(f"❌ Gagal mendapatkan tema: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# === ROUTE: Daftar Tema Tersedia
@utils_bp.route("/themes", methods=["GET"])
def list_available_themes():
    try:
        theme_dir = "static/themes"
        files = [f for f in os.listdir(theme_dir) if f.endswith(".css")]
        return jsonify({"themes": files})
    except Exception as e:
        safe_log(f"❌ Gagal mengambil daftar tema: {e}")
        return jsonify({"error": str(e)}), 500

# === Background heartbeat (setiap 10 menit)
def heartbeat_loop():
    while True:
        safe_log("❤️ Heartbeat: bot masih hidup.")
        time.sleep(600)

# === Fungsi: Jalankan heartbeat
def keep_alive():
    try:
        threading.Thread(target=heartbeat_loop, daemon=True).start()
        threading.Thread(target=update_cpu_usage, daemon=True).start()  # Start CPU update loop
    except Exception as e:
        safe_log(f"❌ Gagal menjalankan heartbeat: {e}")

# === Fungsi: Kirim notifikasi jika bot crash
def notify_crash():
    if NOTIFY_WEBHOOK:
        try:
            requests.post(NOTIFY_WEBHOOK, json={"content": "❌ Bot Satpam mati/crash! Mohon segera cek server."})
            safe_log("📡 Notifikasi crash terkirim.")
        except Exception as e:
            safe_log(f"❌ Gagal mengirim notifikasi crash: {e}")
    else:
        safe_log("⚠️ Webhook notifikasi belum diatur (DISCORD_NOTIFY_WEBHOOK).")

# === Fungsi: Logging saat startup
def log_startup():
    safe_log("🚀 SatpamBot berhasil dijalankan.")

# === Fungsi: Hitung uptime
def get_uptime():
    seconds = int(time.time() - START_TIME.timestamp())
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

# === Fungsi: Statistik RAM (MB)
def get_ram_usage():
    return round(psutil.virtual_memory().used / (1024 * 1024), 2)

# === Fungsi: Statistik CPU (%)
def get_cpu_usage():
    return round(CPU_USAGE, 2)

# === Fungsi: Ambil tema aktif
def get_current_theme():
    try:
        with open("config/theme.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            theme_name = data.get("theme", "default.css")
            if not theme_name.endswith(".css"):
                theme_name += ".css"
            return f"/static/themes/{theme_name}"
    except FileNotFoundError:
        safe_log("⚠️ File theme.json tidak ditemukan. Menggunakan tema default.")
        return "/static/themes/default.css"
    except Exception as e:
        safe_log(f"❌ Gagal membaca tema: {e}")
        return "/static/themes/default.css"

# === Fungsi: Simpan tema baru
def set_theme(theme_name):
    try:
        if not theme_name.endswith(".css"):
            theme_name += ".css"
        theme_path = os.path.join("static", "themes", theme_name)
        if not os.path.isfile(theme_path):
            raise FileNotFoundError(f"Tema {theme_name} tidak ditemukan di /static/themes/")
        
        os.makedirs("config", exist_ok=True)
        with open("config/theme.json", "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f, indent=2)
        safe_log(f"🎨 Tema berhasil diubah ke {theme_name}")
    except Exception as e:
        safe_log(f"❌ Gagal menyimpan tema: {e}")
        raise
