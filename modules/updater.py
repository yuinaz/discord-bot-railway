import subprocess, os, sys, datetime, threading, requests
from flask import redirect, session
from modules.utils import app

NOTIFY_WEBHOOK = os.getenv("DISCORD_NOTIFY_WEBHOOK")

@app.route("/update")
def update():
    if not session.get("admin"): return redirect("/login")
    try:
        output = subprocess.check_output(["git", "pull"]).decode()
        with open("update_log.txt", "a") as log:
            log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Auto update: {output}\n")
    except Exception as e:
        return f"Gagal update: {e}", 500
    return redirect("/restart")

@app.route("/restart")
def restart():
    if not session.get("admin"): return redirect("/login")
    if NOTIFY_WEBHOOK:
        try:
            requests.post(NOTIFY_WEBHOOK, json={"content": "♻️ Bot direstart via dashboard"})
        except: pass
    threading.Thread(target=lambda: os.execv(sys.executable, [sys.executable] + sys.argv)).start()
    return "<meta http-equiv='refresh' content='2;url=/dashboard'><p>Merestart bot...</p>"