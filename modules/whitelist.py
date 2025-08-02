import json
import os
import datetime
from flask import request, redirect, session
from modules.utils import app

WHITELIST_FILE = "whitelist.json"

# === Untuk dashboard.py
def load_config():
    if not os.path.exists(WHITELIST_FILE):
        return {"whitelist": []}
    try:
        with open(WHITELIST_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"whitelist": []}

def save_config(config):
    try:
        with open(WHITELIST_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print("❌ Gagal menyimpan whitelist:", e)

# === Untuk route POST whitelist editor dari dashboard
@app.route("/whitelist", methods=["POST"])
def save_whitelist():
    if not session.get("admin"):
        return redirect("/login")
    try:
        text = request.form.get("domains", "")
        domains = [d.strip() for d in text.splitlines() if d.strip()]
        config = {"whitelist": domains}
        save_config(config)
        with open("whitelist_log.txt", "a") as log:
            log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Whitelist diperbarui oleh admin\n")
    except Exception as e:
        return f"Gagal menyimpan: {e}", 500
    return redirect("/dashboard")
