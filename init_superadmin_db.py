# init_superadmin_db.py

import sqlite3
import os
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "superadmin.db"
USERNAME = os.getenv("SUPER_ADMIN_USER", "admin")
PASSWORD = os.getenv("SUPER_ADMIN_PASS", "Musedash1234")

hashed = generate_password_hash(PASSWORD)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS superadmin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Update jika sudah ada
cursor.execute("SELECT * FROM superadmin WHERE username = ?", (USERNAME,))
if cursor.fetchone():
    cursor.execute("UPDATE superadmin SET password = ? WHERE username = ?", (hashed, USERNAME))
    print(f"🔄 Password admin '{USERNAME}' diupdate.")
else:
    cursor.execute("INSERT INTO superadmin (username, password) VALUES (?, ?)", (USERNAME, hashed))
    print(f"✅ Admin baru '{USERNAME}' ditambahkan.")

conn.commit()
conn.close()
