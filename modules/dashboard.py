from flask import Blueprint, render_template, session, redirect, jsonify
from modules.utils import get_uptime, get_ram_usage, get_cpu_usage, get_current_theme
import sqlite3

dashboard_bp = Blueprint("dashboard", __name__)

# === Halaman Dashboard Utama ===
@dashboard_bp.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")

    username = session.get("username", "Admin")

    try:
        uptime = get_uptime()
    except:
        uptime = "0h 0m 0s"

    try:
        ram_usage = get_ram_usage()
    except:
        ram_usage = "0.00"

    try:
        cpu_usage = get_cpu_usage()
    except:
        cpu_usage = "0.00"

    theme_path = get_current_theme()

    return render_template("dashboard.html",
        uptime=uptime,
        ram_usage=ram_usage,
        cpu_usage=cpu_usage,
        theme_path=theme_path,
        username=username
    )

# === Halaman Grafik ===
@dashboard_bp.route("/grafik")
def grafik():
    if not session.get("logged_in"):
        return redirect("/login")
    try:
        return render_template("grafik.html")
    except:
        return "❌ File grafik.html tidak ditemukan.", 500

# === Halaman Settings ===
@dashboard_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        return redirect("/login")
    try:
        return render_template("settings.html")
    except:
        return "❌ File settings.html tidak ditemukan.", 500

# === Halaman Admin Log ===
@dashboard_bp.route("/admin-log")
def admin_log():
    if not session.get("logged_in"):
        return redirect("/login")
    try:
        return render_template("admin_log.html")
    except:
        return "❌ File admin_log.html tidak ditemukan.", 500

# === API Statistik Server (untuk Chart.js di grafik.html) ===
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
        # Fallback jika tabel tidak ada
        dummy = [
            {"guild_id": "1", "guild_name": "DummyServer", "total_detected": 10},
            {"guild_id": "2", "guild_name": "SatpamBot Dev", "total_detected": 3}
        ]
        return jsonify(dummy)
