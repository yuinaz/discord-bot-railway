import threading
import datetime
import os
import time
import requests
import psutil
from flask import Flask

# === Path fix agar Flask tahu lokasi template/static ===
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, "..", "templates")
static_dir = os.path.join(base_dir, "..", "static")

# === Flask App ===
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")
app.permanent_session_lifetime = datetime.timedelta(minutes=30)

NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")
START_TIME = time.time()

# === Routes ===
@app.route("/ping")
def ping():
    return "✅ Bot is alive!", 200

# === Flask & Heartbeat Thread ===
def run_flask():
    port_str = os.environ.get("PORT")
    try:
        port = int(port_str) if port_str and port_str.isdigit() else 8080
    except Exception as e:
        print("❌ Gagal membaca PORT:", e)
        port = 8080

    print(f"🌐 Menjalankan Flask di port {port}...")
    app.run(host='0.0.0.0', port=port)

def heartbeat_loop():
    while True:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❤️ Heartbeat: bot masih hidup.")
        time.sleep(600)  # 10 menit

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

# === Statistik: uptime, RAM, CPU
def get_uptime():
    seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_ram_usage():
    return round(psutil.virtual_memory().used / (1024 * 1024), 2)  # MB

def get_cpu_usage():
    return round(psutil.cpu_percent(interval=0.5), 2)
