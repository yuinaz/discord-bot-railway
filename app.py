
# --- Secure login merge (use superadmin hashed password) ---
from werkzeug.security import check_password_hash, generate_password_hash

def ensure_admin_seed():
    username = os.getenv("SUPER_ADMIN_USER") or os.getenv("ADMIN_USERNAME") or "admin"
    raw_pwd = (
        os.getenv("SUPER_ADMIN_PASSWORD")
        or os.getenv("SUPER_ADMIN_PASS")
        or os.getenv("ADMIN_PASSWORD")
        or "admin"
    )
    # Make sure DB & table exist
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT id, password FROM superadmin WHERE username=?", (username,))
        row = cur.fetchone()
        pwd_hash = generate_password_hash(raw_pwd)
        if row:
            # keep existing if hash already matches a bcrypt/werkzeug style
            try:
                # If password seems plain, upgrade to hash
                if not row[1] or len(row[1]) < 25:
                    conn.execute("UPDATE superadmin SET password=? WHERE id=?", (pwd_hash, row[0]))
            except Exception:
                conn.execute("UPDATE superadmin SET password=? WHERE id=?", (pwd_hash, row[0]))
        else:
            conn.execute("INSERT INTO superadmin (username, password) VALUES (?,?)", (username, pwd_hash))
        conn.commit()

@app.route("/login", methods=["GET","POST"])
def login():
    # Seed admin on first visit if needed
    try:
        ensure_admin_seed()
    except Exception as e:
        print("[login] seed error:", e)
    error = None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if not u or not p:
            error = "Lengkapi username & password."
        else:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT password FROM superadmin WHERE username=?", (u,)).fetchone()
            if row and check_password_hash(row[0], p):
                session["logged_in"] = True
                session["username"] = u
                return redirect(request.args.get("next") or "/dashboard")
            else:
                error = "Username atau password salah."
    # Optional bot avatar for the login page (if you pass it in context elsewhere)
    return render_template("login.html", error=error, bot_avatar=os.getenv("BOT_AVATAR_URL"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
