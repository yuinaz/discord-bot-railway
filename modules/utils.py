
from flask import Blueprint, request, jsonify
import threading
import datetime
import os
import time
import requests
import psutil
import json

utils_bp = Blueprint("utils", __name__)

NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")
START_TIME = time.time()

@utils_bp.route("/ping")
def ping():
    return "✅ Bot is alive!", 200

def heartbeat_loop():
    while True:
        print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ❤️ Heartbeat: bot masih hidup.")
        time.sleep(600)

def keep_alive():
    try:
        threading.Thread(target=heartbeat_loop, daemon=True).start()
    except Exception as e:
        print("❌ Gagal menjalankan keep_alive():", e)

def notify_crash():
    if NOTIFY_WEBHOOK:
        try:
            requests.post(NOTIFY_WEBHOOK, json={"content": "❌ Bot Satpam mati/crash! Mohon segera cek server."})
            print("📡 Notifikasi crash terkirim.")
        except Exception as e:
            print("❌ Gagal mengirim notifikasi crash:", e)
    else:
        print("⚠️ Webhook untuk notifikasi crash belum diatur.")

def log_startup():
    print(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] 🚀 SatpamBot berhasil dijalankan.")

def get_uptime():
    seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_ram_usage():
    return round(psutil.virtual_memory().used / (1024 * 1024), 2)

def get_cpu_usage():
    return round(psutil.cpu_percent(interval=0.5), 2)

def get_current_theme():
    try:
        with open("config/theme.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return f"themes/{data.get('theme', 'default')}.css"
    except:
        return "themes/default.css"
