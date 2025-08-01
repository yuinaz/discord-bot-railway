from flask import request, redirect, session
from modules.utils import app
import datetime

@app.route("/whitelist", methods=["POST"])
def save_whitelist():
    if not session.get("admin"): return redirect("/login")
    try:
        text = request.form.get("domains", "")
        with open("whitelist.txt", "w") as f:
            f.write(text.strip() + "\n")
        with open("whitelist_log.txt", "a") as log:
            log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Whitelist diperbarui oleh admin\n")
    except Exception as e:
        return f"Gagal menyimpan: {e}", 500
    return redirect("/dashboard")