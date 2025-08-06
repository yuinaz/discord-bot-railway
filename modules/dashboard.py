from flask import Blueprint, render_template, session, redirect, jsonify, request
from modules.utils import get_uptime, get_ram_usage, get_cpu_usage, get_current_theme, set_theme
import sqlite3
import os

dashboard_bp = Blueprint("dashboard", __name__)

# === Halaman Dashboard Utama ===
@dashboard_bp.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

    username = session.get("username", "Admin")
    return render_template("dashboard.html",
        uptime=get_uptime(),
        ram_usage=get_ram_usage(),
        cpu_usage=get_cpu_usage(),
        theme_path=get_current_theme(),
        username=username
    )

# === Halaman Grafik ===
@dashboard_bp.route("/grafik")
def grafik():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("grafik.html", username=session.get("username", "Admin"))

# === Halaman Settings ===
@dashboard_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("settings.html", username=session.get("username", "Admin"))

# === Halaman Admin Log ===
@dashboard_bp.route("/admin-log")
def admin_log():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("admin_log.html", username=session.get("username", "Admin"))

# === API: Statistik Server (Chart.js) ===
@dashboard_bp.route("/api/server_stats")
def server_stats():
    if not session.get("logged_in"):
        return redirect("/login")

    try:
        conn = sqlite3.connect("superadmin.db")
        cursor = conn.cursor()
        cursor.execute("""
        SELECT guild_id, guild_name, COUNT(*) as total_detected
        FROM phishing_logs
        GROUP BY guild_id, guild_name
        """)
        rows = cursor.fetchall()
        conn.close()

        data = [
            {
                "guild_id": row[0],
                "guild_name": row[1],
                "total_detected": row[2]
            } for row in rows
        ]
        return jsonify(data)
    except Exception as e:
        dummy = [
            {"guild_id": "1", "guild_name": "DummyServer", "total_detected": 10},
            {"guild_id": "2", "guild_name": "SatpamBot Dev", "total_detected": 3}
        ]
        return jsonify(dummy)

# === API: Monitor Jumlah Member Aktif (Real-time) ===
@dashboard_bp.route("/api/member_monitor")
def member_monitor():
    if not session.get("logged_in"):
        return redirect("/login")

    try:
        conn = sqlite3.connect("superadmin.db")
        cursor = conn.cursor()
        cursor.execute("SELECT guild_id, guild_name, member_count FROM guilds")
        rows = cursor.fetchall()
        conn.close()

        data = [
            {
                "guild_id": row[0],
                "guild_name": row[1],
                "member_count": row[2]
            } for row in rows
        ]
        return jsonify(data)
    except Exception as e:
        dummy = [
            {"guild_id": "1", "guild_name": "DummyServer", "member_count": 300},
            {"guild_id": "2", "guild_name": "SatpamBot Dev", "member_count": 120}
        ]
        return jsonify(dummy)

# === Halaman Ganti Tema (Form POST versi lama) ===
@dashboard_bp.route("/themes", methods=["GET", "POST"])
def themes():
    if not session.get("logged_in"):
        return redirect("/login")

    if request.method == "POST":
        selected_theme = request.form.get("theme")
        if selected_theme:
            set_theme(selected_theme.replace(".css", ""))
        return redirect("/dashboard")

    return render_template("themes.html", username=session.get("username", "Admin"))

# === API Ganti Tema via POST (AJAX baru) ===
@dashboard_bp.route("/theme", methods=["POST"])
def theme_api_post():
    if not session.get("logged_in"):
        return jsonify({"status": "unauthorized"}), 401

    try:
        data = request.get_json()
        selected_theme = data.get("theme")
        if selected_theme:
            set_theme(selected_theme.replace(".css", ""))
            return jsonify({"status": "success", "theme": selected_theme})
        return jsonify({"status": "error", "message": "Tema tidak valid"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# === Render halaman tambahan secara dinamis ===
def secure_render(page_name):
    if not session.get("logged_in"):
        return redirect("/login")
    try:
        return render_template(f"{page_name}.html", username=session.get("username", "Admin"))
    except:
        return f"❌ File {page_name}.html tidak ditemukan.", 500

# === Register Halaman Tambahan ===
from functools import partial

pages = [
    "log_ai", "chat", "embed2", "event_log", "heatmap", "landing",
    "logout", "notifikasi", "phishing", "plugin", "poll", "profil",
    "resource", "role_maker", "scheduler", "server_summary",
    "user_locator", "editor", "backup",
    "change_password", "change-password", "sso"
]

for page in pages:
    route_path = f"/{page.replace('_', '-')}" if '-' in page else f"/{page}"
    dashboard_bp.add_url_rule(route_path, endpoint=page, view_func=partial(secure_render, page))
