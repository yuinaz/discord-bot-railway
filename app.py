from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
import os

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
app.secret_key = os.getenv("FLASK_SECRET", "supersecretkey")

# ===== DATABASE SETUP =====
DB_PATH = "superadmin.db"
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS superadmin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        # Buat admin default jika belum ada
        cur = conn.execute("SELECT COUNT(*) FROM superadmin")
        if cur.fetchone()[0] == 0:
            conn.execute("INSERT INTO superadmin (username, password) VALUES (?, ?)",
                         ("admin", generate_password_hash("admin123")))

# ===== ROUTES =====
@app.route("/")
def home():
    return redirect("/dashboard") if session.get("logged_in") else redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect("/dashboard")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        remember = request.form.get("remember")
        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute("SELECT * FROM superadmin WHERE username=?", (username,)).fetchone()
            if user and check_password_hash(user[2], password):
                session["logged_in"] = True
                session["username"] = username
                if remember:
                    session.permanent = True
                return redirect("/dashboard")
        return redirect("/login?error=gagal")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return render_template("logout.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        return redirect("/login")
    if request.method == "POST":
        # simpan konfigurasi ke file/env/DB (dummy di sini)
        print("Disimpan:", request.form)
        return redirect("/settings")
    return render_template("settings.html")

@app.route("/grafik")
def grafik():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("grafik.html")

@app.route("/profil")
def profil():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("profil.html")

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("logged_in"):
        return redirect("/login")
    if request.method == "POST":
        old_pw = request.form["old_password"]
        new_pw = request.form["new_password"]
        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute("SELECT * FROM superadmin WHERE username=?", (session["username"],)).fetchone()
            if user and check_password_hash(user[2], old_pw):
                conn.execute("UPDATE superadmin SET password=? WHERE username=?",
                             (generate_password_hash(new_pw), session["username"]))
                return redirect("/change-password?success=1")
            else:
                return redirect("/change-password?error=1")
    return render_template("change-password.html")

@app.route("/api/user-stats")
def user_stats():
    if not session.get("logged_in"):
        return redirect("/login")
    # Dummy data
    return {
        "labels": ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
        "values": [12, 15, 10, 20, 14, 18, 16]
    }

# ===== MAIN =====
if __name__ == "__main__":
    init_db()
    socketio.run(debug=True, port=5000)
\n
# ===== START DISCORD BOT IN BACKGROUND =====
import threading
from discord_bot import run_discord_bot

bot_thread = threading.Thread(target=run_discord_bot)
bot_thread.start()


from database import init_stats_db, get_last_7_days

@app.route("/api/user-stats")
def user_stats():
    if not session.get("logged_in"):
        return redirect("/login")
    data = get_last_7_days()
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    return {"labels": labels, "values": values}

# Init database statistik
init_stats_db()


@app.route("/api/server-stats/<guild_id>")
def server_stats(guild_id):
    if not session.get("logged_in"):
        return redirect("/login")
    data = get_stats_last_7_days(guild_id)
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    return {"labels": labels, "values": values}


@socketio.on('connect')
def handle_connect():
    print("📡 Client terhubung ke SocketIO")

@socketio.on('disconnect')
def handle_disconnect():
    print("📴 Client terputus")

def broadcast_stat_update():
    from database import get_stats_all_guilds
    socketio.emit("update_stats", {"data": get_stats_all_guilds()})


@app.route("/api/join-leave/<guild_id>")
def api_join_leave(guild_id):
    from database import get_hourly_join_leave
    rows = get_hourly_join_leave(guild_id)
    hours = []
    joins = []
    leaves = []
    for hour, j, l in rows:
        hours.append(f"{hour}:00")
        joins.append(j)
        leaves.append(l)
    return jsonify({
        "hours": hours,
        "joins": joins,
        "leaves": leaves
    })
