import aiosqlite
import sqlite3
import os

# 🔄 Lokasi file database
DB_PATH = os.getenv("DB_PATH", "data.db")
STATS_DB = "stats.db"

# ======================
# 📊 Statistik Bot
# ======================

def get_stats_last_7_days(guild_id):
    with sqlite3.connect(STATS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, COUNT(*) 
            FROM user_activity 
            WHERE guild_id = ? 
            GROUP BY date 
            ORDER BY date DESC 
            LIMIT 7
        """, (guild_id,))
        return cursor.fetchall()

def get_hourly_join_leave(guild_id):
    with sqlite3.connect(STATS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT hour, SUM(joins), SUM(leaves) 
            FROM join_leave 
            WHERE guild_id = ? 
            GROUP BY hour 
            ORDER BY hour
        """, (guild_id,))
        return cursor.fetchall()

def get_stats_all_guilds():
    with sqlite3.connect(STATS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT guild_id, COUNT(DISTINCT user_id) 
            FROM user_activity 
            GROUP BY guild_id
        """)
        return [{"guild_id": row[0], "user_count": row[1]} for row in cursor.fetchall()]

def generate_empty_stats_db():
    """Buat file stats.db kosong jika belum ada."""
    if not os.path.exists(STATS_DB):
        try:
            with sqlite3.connect(STATS_DB) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        guild_id TEXT,
                        date TEXT
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS join_leave (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id TEXT,
                        hour INTEGER,
                        joins INTEGER,
                        leaves INTEGER
                    )
                """)
                conn.commit()
            print("[📊] stats.db berhasil digenerate (kosong)")
        except Exception as e:
            print(f"[❌] Gagal membuat stats.db: {e}")

# ======================
# 🧠 Log Aktifitas Bot
# ======================

async def init_db():
    """Inisialisasi database log async dan buat tabel jika belum ada."""
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
    """Simpan log ke tabel logs."""
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
