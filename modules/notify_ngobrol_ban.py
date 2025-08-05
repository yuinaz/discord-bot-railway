from flask import Blueprint, request, redirect, session
import datetime

notify_ngobrol_ban_bp = Blueprint("notify_ngobrol_ban", __name__)

@notify_ngobrol_ban_bp.route("/notify", methods=["POST"])
def notify_ngobrol_ban():
    if not session.get("admin"):
        return redirect("/login")

    content = request.form.get("content", "").strip()
    if not content:
        return "Konten tidak boleh kosong", 400

    log_entry = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] Notifikasi Ngobrol/Ban: {content}\n"
    try:
        with open("notify_log.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        return f"Gagal menyimpan notifikasi: {e}", 500

    return redirect("/dashboard")
