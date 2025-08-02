import asyncio
import os
import sqlite3
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

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

    # 🔥 Hapus file lama (opsional, hanya untuk deploy pertama!)
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

# === Main async ===
async def main():
    # Setup DB
    generate_empty_stats_db()
    await init_db()
    ensure_superadmin()

    # Aktifkan Flask & heartbeat
    keep_alive()
    log_startup()

    # Ambil token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ DISCORD_TOKEN belum diatur di .env")
    print(f"🔐 Token dimuat, panjang: {len(token)} karakter")

    # Jalankan bot
    await bot.start(token)

# === Jalankan ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[❌ ERROR] {e}")
