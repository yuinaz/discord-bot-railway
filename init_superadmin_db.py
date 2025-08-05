# init_superadmin_db.py

import sqlite3
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load dari .env jika ada
load_dotenv()

# Konfigurasi
DB_PATH = "superadmin.db"
USERNAME = os.getenv("SUPER_ADMIN_USER", "admin")
PASSWORD = os.getenv("SUPER_ADMIN_PASS", "Musedash123")

# Koneksi ke database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Buat tabel superadmin
cursor.execute("""
CREATE TABLE IF NOT EXISTS superadmin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Buat tabel histori admin (login/ganti password)
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Masukkan user admin (jika belum ada)
hashed = generate_password_hash(PASSWORD)
cursor.execute("INSERT OR IGNORE INTO superadmin (username, password) VALUES (?, ?)", (USERNAME, hashed))

conn.commit()
conn.close()

print(f"✅ superadmin.db berhasil dibuat. Akun admin: {USERNAME}")
