import aiosqlite
import os

# Path database (bisa diatur lewat environment)
DB_PATH = os.getenv("DB_PATH", "data.db")

async def init_db():
    """
    Inisialisasi database SQLite dan buat tabel logs jika belum ada.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    action TEXT,
                    content TEXT,
                    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            await db.commit()
            print("[✅] Database berhasil diinisialisasi.")
    except Exception as e:
        print(f"[❌] Gagal inisialisasi database: {e}")

async def save_log(user_id, username, action, content):
    """
    Simpan satu entri log ke database.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO logs (user_id, username, action, content) VALUES (?, ?, ?, ?)",
                (user_id, username, action, content)
            )
            await db.commit()
            print(f"[📄] Log disimpan untuk {username} ({user_id}) - {action}")
    except Exception as e:
        print(f"[❌] Gagal menyimpan log: {e}")
