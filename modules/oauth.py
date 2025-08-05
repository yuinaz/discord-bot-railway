from flask import Blueprint, render_template, request, redirect, session
import sqlite3
from werkzeug.security import check_password_hash

oauth_bp = Blueprint("oauth", __name__)
print("✅ oauth_bp loaded and registered.")  # DEBUG: memastikan blueprint dimuat

DB_PATH = "superadmin.db"

# === Login Page ===
@oauth_bp.route("/login", methods=["GET", "POST"])
def login():
    print("🔐 /login route accessed.")  # DEBUG: memastikan route dijalankan

    if session.get("logged_in"):
        print("ℹ️ Sudah login. Redirect ke /dashboard.")
        return redirect("/dashboard")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        print(f"📝 Login POST - Username: {username}")

        try:
            with sqlite3.connect(DB_PATH) as conn:
                user = conn.execute("SELECT * FROM superadmin WHERE username=?", (username,)).fetchone()
                if user:
                    print("✅ User ditemukan di database.")
                else:
                    print("❌ Username tidak ditemukan di database.")

                if user and check_password_hash(user[2], password):
                    print("🔓 Password valid. Login sukses.")
                    session["logged_in"] = True
                    session["admin"] = True
                    session["username"] = username
                    return redirect("/dashboard")
                else:
                    print("❌ Password salah.")
        except Exception as e:
            print(f"🔥 ERROR saat login: {e}")

        return render_template("login.html", error="❌ Username atau password salah.")

    # Jika GET, tampilkan form login
    return render_template("login.html")

# === Logout ===
@oauth_bp.route("/logout")
def logout():
    print("🚪 Logout berhasil. Session dibersihkan.")
    session.clear()
    return redirect("/login")
