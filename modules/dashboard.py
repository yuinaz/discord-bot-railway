import sqlite3
from flask import request, redirect, session, render_template, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from modules.utils import app, get_uptime, get_ram_usage, get_cpu_usage
from modules.whitelist import load_config, save_config
from modules.database import get_stats_last_7_days, get_stats_all_guilds, get_hourly_join_leave

DB_PATH = "superadmin.db"

# ====================================
# 🔐 Superadmin DB & Autentikasi
# ====================================

def get_user(username):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM superadmin WHERE username = ?", (username,))
        return cursor.fetchone()

def log_activity(username, action):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO admin_history (username, action) VALUES (?, ?)", (username, action))
        conn.commit()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username)

        if user and check_password_hash(user[2], password):
            session["logged_in"] = True
            session["username"] = username
            if "remember" in request.form:
                session.permanent = True
            log_activity(username, "Login")
            return redirect("/dashboard")
        else:
            flash("Login gagal. Username atau password salah.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout", "info")
    return redirect("/login")

# ====================================
# 📊 Dashboard
# ====================================

@app.route("/dashboard")
def dashboard():
    if "logged_in" not in session:
        return redirect("/login")
    return render_template("dashboard.html",
                           uptime=get_uptime(),
                           ram_usage=get_ram_usage(),
                           cpu_usage=get_cpu_usage())

# ====================================
# 🔑 Ganti Password
# ====================================

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "logged_in" not in session:
        return redirect("/login")

    username = session["username"]
    user = get_user(username)

    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not check_password_hash(user[2], old_password):
            flash("Password lama salah", "danger")
            return redirect("/change-password")

        if new_password != confirm_password:
            flash("Konfirmasi password tidak cocok", "danger")
            return redirect("/change-password")

        hashed_new = generate_password_hash(new_password)
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE superadmin SET password = ? WHERE username = ?", (hashed_new, username))
            conn.commit()

        log_activity(username, "Change Password")
        flash("Password berhasil diganti!", "success")
        return redirect("/dashboard")

    return render_template("change_password.html")

# ====================================
# 📜 Log Aktivitas Admin
# ====================================

@app.route("/admin-log")
def admin_log():
    if "logged_in" not in session:
        return redirect("/login")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, action, timestamp FROM admin_history ORDER BY timestamp DESC")
        logs = cursor.fetchall()

    return render_template("admin_log.html", logs=logs)

# ====================================
# ⚙️ Pengaturan Bot
# ====================================

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "logged_in" not in session:
        return redirect("/login")

    config = load_config()

    if request.method == "POST":
        config["AUTO_BAN"] = request.form.get("AUTO_BAN") == "on"
        config["ADMIN_IDS"] = [x.strip() for x in request.form.get("ADMIN_IDS", "").split(",")]
        config["NOTIFY_WEBHOOK"] = request.form.get("NOTIFY_WEBHOOK", "")
        save_config(config)
        flash("Pengaturan disimpan", "success")

    return render_template("settings.html", config=config)

# ====================================
# 📈 Grafik Statistik & API
# ====================================

@app.route("/grafik")
def grafik():
    if "logged_in" not in session:
        return redirect("/login")
    return render_template("grafik.html")

@app.route("/api/stats/<guild_id>")
def api_stats_per_server(guild_id):
    if "logged_in" not in session:
        return redirect("/login")

    data = get_stats_last_7_days(guild_id)
    return jsonify({
        "dates": [d[0] for d in data],
        "counts": [d[1] for d in data]
    })

@app.route("/api/join-leave/<guild_id>")
def api_join_leave(guild_id):
    if "logged_in" not in session:
        return redirect("/login")

    rows = get_hourly_join_leave(guild_id)
    return jsonify({
        "hours": [f"{r[0]}:00" for r in rows],
        "joins": [r[1] for r in rows],
        "leaves": [r[2] for r in rows]
    })

@app.route("/api/server_stats")
def api_all_stats():
    if "logged_in" not in session:
        return redirect("/login")
    return jsonify(get_stats_all_guilds())
