
import sqlite3
from flask import request, redirect, session, render_template, flash
from werkzeug.security import check_password_hash, generate_password_hash
from modules.utils import app, get_uptime, get_ram_usage, get_cpu_usage

DB_PATH = "superadmin.db"

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
        flash("Login gagal", "danger")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "logged_in" not in session:
        return redirect("/login")
    return render_template("dashboard.html",
                           uptime=get_uptime(),
                           ram_usage=get_ram_usage(),
                           cpu_usage=get_cpu_usage())

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

@app.route("/admin-log")
def admin_log():
    if "logged_in" not in session:
        return redirect("/login")
    import sqlite3
    with sqlite3.connect("superadmin.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, action, timestamp FROM admin_history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
    return render_template("admin_log.html", logs=rows)
