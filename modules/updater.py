from flask import Blueprint, session, redirect, current_app as app
import subprocess
import os
import sys
import datetime
import threading
import requests

updater_bp = Blueprint("updater", __name__)

NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")

@updater_bp.route("/update")
def update():
    if not session.get("admin"):
        return redirect("/login")
    try:
        output = subprocess.check_output(["git", "pull"]).decode()
        with open("update_log.txt", "a", encoding="utf-8") as log:
            log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Auto update:\n{output}\n")
        print("✅ Update berhasil:\n", output)
    except Exception as e:
        print("❌ Gagal update:", e)
        return f"Gagal update: {e}", 500

    return redirect("/restart")

@updater_bp.route("/restart")
def restart():
    if not session.get("admin"):
        return redirect("/login")

    if NOTIFY_WEBHOOK:
        try:
            requests.post(NOTIFY_WEBHOOK, json={"content": "♻️ Bot direstart via dashboard"})
            print("📡 Notifikasi restart terkirim.")
        except Exception as e:
            print("❌ Gagal mengirim notifikasi restart:", e)

    # Restart app using current python executable
    threading.Thread(target=lambda: os.execv(sys.executable, [sys.executable] + sys.argv)).start()
    return "<meta http-equiv='refresh' content='2;url=/dashboard'><p>♻️ Merestart bot...</p>"
