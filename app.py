
import os, json, time, sqlite3
from flask import Flask, render_template, request, redirect, session, jsonify, send_from_directory, flash
from werkzeug.utils import secure_filename
from functools import wraps

# Optional libs used by endpoints
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

# ---------------------------
# Auth helper
# ---------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect("/login")
        return view(*args, **kwargs)
    return wrapped

# ---------------------------
# DB bootstrap (safe)
# ---------------------------
def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS superadmin (
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
            CREATE TABLE IF NOT EXISTS bot_guilds (
                guild_id TEXT PRIMARY KEY,
                name TEXT,
                member_count INTEGER,
                icon_url TEXT,
                joined_at TEXT
            )
        """)
        conn.commit()

# ---------------------------
# Theme & background helpers
# ---------------------------
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
    theme_file = (cfg.get("theme") or "cyberpunk.css").strip()
    if not theme_file.endswith(".css"):
        theme_file += ".css"
    if not os.path.exists(os.path.join("static","themes", theme_file)):
        theme_file = "cyberpunk.css"
    return f"/static/themes/{theme_file}"

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

@app.context_processor
def inject_globals():
    return {
        "theme_path": get_theme_path(),
        "background_url": _load_background_url(),
        "cache_bust": int(time.time()),
        "invite_url": _invite_url(),
        "session": session,
    }

# ---------------------------
# Routes: auth (minimal)
# ---------------------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        # VERY simple login for demo; replace with your own
        session["logged_in"] = True
        session["username"] = "admin"
        return redirect("/dashboard")
    return "<form method='post'><button>Login</button></form>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------------------
# Routes: dashboard + servers
# ---------------------------
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

# ---------------------------
# API: theme & background
# ---------------------------
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
        # no theme provided → return current
        return jsonify({"status":"ok","theme": get_theme_path().rsplit("/",1)[-1]})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)}), 500

@app.route("/upload/background", methods=["POST"])
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

    # Resize + compress when Pillow available
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

# ---------------------------
# API: dashboard data
# ---------------------------
@app.route("/api/dashboard")
@login_required
def api_dashboard():
    # KPIs from psutil if present
    cpu = round(psutil.cpu_percent(interval=0.1),1) if psutil else 0.0
    ram_mb = int(psutil.virtual_memory().used/1024/1024) if psutil else 0
    uptime = 0
    if psutil:
        uptime = int(time.time() - psutil.boot_time())
    up_str = f"{uptime//3600:02d}:{(uptime%3600)//60:02d}:{uptime%60:02d}"

    # Series (fake but stable demo)
    labels = [f"D-{i}" for i in range(6,-1,-1)]
    values = [18,26,33,29,41,45,52]

    # Guilds (top 6) from DB
    guilds = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT name, member_count AS detections FROM bot_guilds ORDER BY detections DESC LIMIT 6").fetchall()
            guilds = [dict(r) for r in rows]
    except Exception:
        pass

    # Bans
    bans = []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
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

# ---------------------------
# Servers API minimal
# ---------------------------
@app.route("/api/guilds")
@login_required
def api_guilds():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bot_guilds ORDER BY LOWER(name)").fetchall()
        return jsonify([dict(r) for r in rows])

# ---------------------------
# Start helpers
# ---------------------------

# ---- EXTRA DASHBOARD DATA (for neon layout) ----
@app.route("/api/dashboard_plus")
@login_required
def api_dashboard_plus():
    # Reuse /api/dashboard for base data
    try:
        base_resp = api_dashboard()
        if hasattr(base_resp, "get_json"):
            base = base_resp.get_json()
        else:
            base = json.loads(base_resp.get_data(as_text=True))
    except Exception:
        base = {"kpi":{"cpu":0,"ram":0,"uptime":"00:00:00"},
                "series":{"labels":[],"values":[]},
                "guilds":[], "bans":[]}

    # Mini line strips (3)
    mini = [
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[12,18,22,25,21,28,32]},
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[22,24,19,26,29,27,31]},
        {"labels":["Mo","Tu","We","Th","Fr","Sa","Su"], "values":[9,12,11,15,13,17,20]},
    ]

    # Four circular gauges
    gauges = [98, 65, 83, 37]

    # Tall bar series
    bar_labels = [str(i) for i in range(1,13)]
    bar_values = [36,48,28,52,44,61,57,63,54,37,42,66]

    # Dot-matrix 7x7 (0..5 intensity)
    heat = [[(i*j) % 6 for i in range(7)] for j in range(7)]

    # Bottom counters
    counters = {"MAGNA":74, "DOLOR":65, "VELIT":83, "ABETS":37}

    # Big donut center value
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


def bootstrap():
    init_db()

# (socketio main omitted; run with `python main.py` which imports app/bootstrap)
