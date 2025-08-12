
import os, json, time, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# Optional deps
try:
    import psutil
except Exception:
    psutil = None

try:
    from PIL import Image, ImageOps
except Exception:
    Image = ImageOps = None

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "changeme")

DB_PATH = os.getenv("DB_PATH", "superadmin.db")

# ---------------- Auth helper ----------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapped

# ---------------- DB bootstrap ----------------
def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS superadmin(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                guild_id TEXT,
                reason TEXT,
                banned_at TEXT,
                active INTEGER DEFAULT 1,
                unbanned_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_guilds(
                id TEXT PRIMARY KEY,
                name TEXT,
                icon_url TEXT
            )""")
        conn.commit()

def ensure_admin_seed():
    username = os.getenv("SUPER_ADMIN_USER") or os.getenv("ADMIN_USERNAME") or "admin"
    raw_pwd = (
        os.getenv("SUPER_ADMIN_PASSWORD")
        or os.getenv("SUPER_ADMIN_PASS")
        or os.getenv("ADMIN_PASSWORD")
        or "admin"
    )
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT id, password FROM superadmin WHERE username=?", (username,)).fetchone()
        pwd_hash = generate_password_hash(raw_pwd)
        if row:
            try:
                if not row[1] or len(row[1]) < 25:
                    conn.execute("UPDATE superadmin SET password=? WHERE id=?", (pwd_hash, row[0]))
            except Exception:
                conn.execute("UPDATE superadmin SET password=? WHERE id=?", (pwd_hash, row[0]))
        else:
            conn.execute("INSERT INTO superadmin (username, password) VALUES (?,?)", (username, pwd_hash))
        conn.commit()

# ---------------- Theme helpers ----------------
def _load_theme_config():
    try:
        return json.load(open(os.path.join("config","theme.json"), "r", encoding="utf-8"))
    except Exception:
        return {}

def list_themes():
    d = os.path.join("static","themes")
    try:
        return sorted([f for f in os.listdir(d) if f.endswith(".css") and not f.startswith("_")])
    except Exception:
        return []

def get_theme_path():
    cfg = _load_theme_config()
    fn = (cfg.get("theme") or "cyberpunk.css").strip()
    if not fn.endswith(".css"): fn += ".css"
    if not os.path.exists(os.path.join("static","themes", fn)): fn = "cyberpunk.css"
    return f"/static/themes/{fn}"

def _load_background_url():
    url = (_load_theme_config().get("background_image") or "").strip()
    if url and not url.startswith(("http://","https://","/")):
        url = "/" + url.lstrip()
    return url

def _invite_url():
    cid = os.getenv("DISCORD_CLIENT_ID") or os.getenv("BOT_CLIENT_ID")
    perms = os.getenv("DISCORD_INVITE_PERMS", "8")
    scope = "bot%20applications.commands"
    return (f"https://discord.com/api/oauth2/authorize?client_id={cid}&permissions={perms}&scope={scope}") if cid else None



def _load_bot_logo_url():
    try:
        url = (_load_theme_config().get("bot_logo") or os.getenv("BOT_AVATAR_URL") or "/static/icon-default.png").strip()
    except Exception:
        url = os.getenv("BOT_AVATAR_URL") or "/static/icon-default.png"
    if url and not url.startswith(("http://","https://","/")):
        url = "/" + url.lstrip()
    return url
@app.context_processor
def inject_globals():
    return {
        "theme_path": get_theme_path(),
        "background_url": _load_background_url(),
        "bot_logo_url": _load_bot_logo_url(),
        "cache_bust": int(time.time()),
        "invite_url": _invite_url(),
        "session": session,
    }


# --- Migration: ensure bot_guilds has 'id' column and unique index

def ensure_bot_guilds_pk():
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.row_factory = sqlite3.Row
            cols = {r[1] for r in conn.execute("PRAGMA table_info(bot_guilds)")}
            if 'id' not in cols and 'guild_id' in cols:
                conn.execute("ALTER TABLE bot_guilds ADD COLUMN id TEXT")
                conn.execute("UPDATE bot_guilds SET id = guild_id WHERE id IS NULL")
            # create index for id
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_guilds_id ON bot_guilds(id)")
            conn.commit()
        except Exception as e:
            # If table doesn't exist yet, create it
            conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_guilds(
                id TEXT PRIMARY KEY,
                name TEXT,
                icon_url TEXT
            )
            """)
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bot_guilds_id ON bot_guilds(id)")
            conn.commit()

# ---------------- Routes: Auth ----------------
@app.route("/login", methods=["GET","POST"])
def login():
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
    return render_template("login.html", error=error, bot_avatar=os.getenv("BOT_AVATAR_URL"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- Routes: Pages ----------------
@app.route("/")
@login_required
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/servers")
@login_required
def servers_page():
    return render_template("servers.html")

@app.route("/settings")
@login_required
def settings_page():
    current_theme = get_theme_path().split("/")[-1]
    return render_template("settings.html",
                           available_themes=list_themes(),
                           current_theme=current_theme,
                           background_current=_load_background_url())

# ---------------- API: Theme & Background ----------------
@app.route("/theme", methods=["GET","POST"])
def change_theme():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            theme = (data.get("theme") or "").strip()
        else:
            theme = (request.args.get("set") or request.args.get("theme") or "").strip()

        if theme and not theme.endswith(".css"):
            theme += ".css"
        if theme:
            path = os.path.join("static","themes", theme)
            if not os.path.exists(path):
                return jsonify({"status":"error","message":"Theme not found"}), 400
            os.makedirs("config", exist_ok=True)
            cfg = _load_theme_config()
            cfg["theme"] = theme
            json.dump(cfg, open(os.path.join("config","theme.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
            return jsonify({"status":"success","theme": theme})
        return jsonify({"status":"ok","theme": get_theme_path().rsplit("/",1)[-1]})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 500

@app.route("/upload/logo", methods=["POST"])
@login_required
def upload_logo():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"status":"error","message":"No file"}), 400
    ext = "." + f.filename.rsplit(".",1)[-1].lower()
    if ext not in {".jpg",".jpeg",".png",".webp",".gif"}:
        return jsonify({"status":"error","message":"Unsupported type"}), 400
    updir = os.path.join("static","uploads")
    os.makedirs(updir, exist_ok=True)
    name = f"logo_{int(time.time())}_" + secure_filename(f.filename)
    path = os.path.join(updir, name)
    try:
        if Image is not None:
            img = Image.open(f.stream)
            try: img = ImageOps.exif_transpose(img)
            except Exception: pass
            img.thumbnail((512,512))
            img.save(path)
        else:
            f.save(path)
    except Exception:
        f.stream.seek(0); f.save(path)
    url = "/" + path.replace("\\","/")
    cfg = _load_theme_config(); cfg["bot_logo"] = url
    os.makedirs("config", exist_ok=True)
    json.dump(cfg, open(os.path.join("config","theme.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    return jsonify({"status":"success","url": url})
("/upload/background", methods=["POST"])
@login_required
def upload_background():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"status":"error","message":"No file"}), 400
    ext = "." + f.filename.rsplit(".",1)[-1].lower()
    if ext not in {".jpg",".jpeg",".png",".webp",".gif"}:
        return jsonify({"status":"error","message":"Unsupported type"}), 400

    updir = os.path.join("static","uploads")
    os.makedirs(updir, exist_ok=True)
    name = f"{int(time.time())}_{secure_filename(f.filename)}"
    path = os.path.join(updir, name)

    if Image is not None:
        try:
            img = Image.open(f.stream)
            try: img = ImageOps.exif_transpose(img)
            except Exception: pass
            img.thumbnail((1920,1080), Image.LANCZOS)
            fmt = "PNG" if ext == ".png" else "JPEG"
            params = {"optimize": True}
            if fmt == "JPEG":
                if img.mode in ("RGBA","LA"):
                    bg = Image.new("RGB", img.size, "#0b0b16"); bg.paste(img, mask=img.split()[-1]); img = bg
                elif img.mode != "RGB": img = img.convert("RGB")
                params.update({"quality": 84, "progressive": True})
            img.save(path, fmt, **params)
        except Exception:
            f.stream.seek(0); f.save(path)
    else:
        f.save(path)

    url = "/" + path.replace("\\","/")
    cfg = _load_theme_config()
    cfg["background_image"] = url
    os.makedirs("config", exist_ok=True)
    json.dump(cfg, open(os.path.join("config","theme.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    return jsonify({"status":"success","url":url})

# ---------------- API: Dashboard data ----------------
@app.route("/api/dashboard")
@login_required
def api_dashboard():
    cpu = round(psutil.cpu_percent(interval=0.1),1) if psutil else 0.0
    ram_mb = int(psutil.virtual_memory().used/1024/1024) if psutil else 0
    up_str = "00:00:00"
    if psutil:
        uptime = int(time.time() - psutil.boot_time())
        up_str = f"{uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}"

    labels = [f"D-{i}" for i in range(6,-1,-1)]
    values = [18,26,33,29,41,45,52]

    guilds = []; bans = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT name, member_count AS detections FROM bot_guilds ORDER BY detections DESC LIMIT 6").fetchall()
            guilds = [dict(r) for r in rows]
            rows = conn.execute("SELECT user_id, username, guild_id, reason FROM banned_users WHERE active=1 ORDER BY banned_at DESC LIMIT 6").fetchall()
            bans = [dict(r) for r in rows]
    except Exception:
        pass

    return jsonify({
        "kpi": {"cpu": cpu, "ram": ram_mb, "uptime": up_str},
        "series": {"labels": labels, "values": values},
        "guilds": guilds,
        "bans": bans
    })

@app.route("/api/dashboard_plus")
@login_required
def api_dashboard_plus():
    base = api_dashboard().get_json()
    mini = [
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[12,18,22,25,21,28,32]},
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[22,24,19,26,29,27,31]},
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[9,12,11,15,13,17,20]},
    ]
    gauges = [98, 65, 83, 37]
    bar_labels = [str(i) for i in range(1,13)]
    bar_values = [36,48,28,52,44,61,57,63,54,37,42,66]
    heat = [[(i*j) % 6 for i in range(7)] for j in range(7)]
    counters = {"MAGNA":74, "DOLOR":65, "VELIT":83, "ABETS":37}
    core_total = 7583930

    return jsonify({
        "base": base,
        "mini": mini,
        "gauges": gauges,
        "barLeft": {"labels": bar_labels, "values": bar_values},
        "heat": heat,
        "counters": counters,
        "core_total": core_total
    })

@app.route("/api/guilds")
@login_required
def api_guilds():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bot_guilds ORDER BY LOWER(name)").fetchall()
        return jsonify([dict(r) for r in rows])

# ---------------- Health ----------------
@app.route("/healthz")
def healthz():
    return jsonify({"status":"ok","ts": int(time.time())}), 200

@app.route("/readyz")
def readyz():
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("SELECT 1")
        return jsonify({"status":"ready"}), 200
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500


@app.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    msg = None
    err = None
    if request.method == "POST":
        old = (request.form.get("old_password") or "").strip()
        new = (request.form.get("new_password") or "").strip()
        confirm = (request.form.get("confirm_password") or "").strip()
        if not new or len(new) < 6:
            err = "Password baru minimal 6 karakter."
        elif new != confirm:
            err = "Konfirmasi password tidak cocok."
        else:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute("SELECT id, password FROM superadmin WHERE username=?", (session.get("username") or "admin",)).fetchone()
                if not row or not check_password_hash(row[1], old):
                    err = "Password lama salah."
                else:
                    conn.execute("UPDATE superadmin SET password=? WHERE id=?", (generate_password_hash(new), row[0]))
                    conn.commit()
                    msg = "Password berhasil diperbarui."
    return render_template("change_password.html", message=msg, error=err)


@app.route("/admin-log")
@login_required
def admin_log():
    return render_template("admin_log.html")


@app.route("/grafik")
@login_required
def grafik():
    return render_template("grafik.html")


@app.route("/blacklist-image")
@login_required
def blacklist_image():
    # Use admin_blacklist template as the editor landing
    return render_template("admin_blacklist.html")


@app.route("/api/guilds/add", methods=["POST"])
@login_required
def api_add_guild():
    data = request.get_json(force=True, silent=True) or {}
    gid = (data.get("id") or "").strip() or str(int(time.time()))
    name = (data.get("name") or "").strip()
    icon_url = (data.get("icon_url") or "").strip()
    if not name:
        return jsonify({"status":"error","message":"Nama server wajib diisi"}), 400
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_guilds(
                id TEXT PRIMARY KEY,
                name TEXT,
                icon_url TEXT
            )
        """)
        # upsert
        row = conn.execute("SELECT id FROM bot_guilds WHERE id=?", (gid,)).fetchone()
        if row:
            conn.execute("UPDATE bot_guilds SET name=?, icon_url=? WHERE id=?", (name, icon_url, gid))
        else:
            conn.execute("INSERT INTO bot_guilds (id, name, icon_url) VALUES (?,?,?)", (gid, name, icon_url))
        conn.commit()
    return jsonify({"status":"ok","id":gid})

# ---------------- Bootstrap ----------------
def bootstrap():
    init_db()
    ensure_bot_guilds_pk()
    ensure_admin_seed()
