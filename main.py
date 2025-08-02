import asyncio
import os
import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from flask import request, render_template, redirect, session, flash

# === Load environment ===
load_dotenv()

# === Import dari modul internal ===
from modules.discord_bot import bot
from modules.utils import keep_alive, log_startup
from modules.database import init_db, generate_empty_stats_db
from modules.dashboard import app

# === Auto-create superadmin.db ===
def ensure_superadmin():
    db_path = "superadmin.db"
    username = "admin"
    password = "Musedash123"

    # 🔥 Hapus file lama (opsional, hanya saat deploy pertama kali!)
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ superadmin.db lama dihapus.")

    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Tabel superadmin
        c.execute("""
            CREATE TABLE IF NOT EXISTS superadmin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # Tabel log
        c.execute("""
            CREATE TABLE IF NOT EXISTS admin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                action TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert admin (hash password)
        hashed = generate_password_hash(password)
        c.execute("INSERT OR IGNORE INTO superadmin (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        print("✅ Superadmin admin berhasil disiapkan.")
    except Exception as e:
        print("❌ Gagal setup superadmin:", e)

# === Editor Route untuk edit main.py ===
@app.route("/editor", methods=["GET"])
def editor_page():
    if "logged_in" not in session:
        return redirect("/login")

    try:
        with open("main.py", "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        code = f"# Error loading file: {e}"
    return render_template("editor.html", code=code)

@app.route("/editor/save", methods=["POST"])
def editor_save():
    if "logged_in" not in session:
        return redirect("/login")

    new_code = request.form.get("code")
    try:
        with open("main.py", "w", encoding="utf-8") as f:
            f.write(new_code)
        flash("✅ File berhasil disimpan", "success")
    except Exception as e:
        flash(f"❌ Gagal menyimpan file: {e}", "danger")

    return redirect("/editor")

# === Fungsi utama ===
async def main():
    generate_empty_stats_db()
    await init_db()
    ensure_superadmin()

    keep_alive()
    log_startup()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ DISCORD_TOKEN belum diatur di .env")
    print(f"🔐 Token dimuat, panjang: {len(token)} karakter")

    await bot.start(token)

# === Jalankan ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[❌ ERROR] {e}")
