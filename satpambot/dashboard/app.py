
import os

from functools import wraps
from flask import session, redirect, url_for, request

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not (session.get("admin") or session.get("oauth") or session.get("discord_user")):
            return redirect(url_for("login", next=request.url))
        return fn(*args, **kwargs)
    return wrapper
import json
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SESSION_SECRET", os.getenv("SECRET_KEY", "satpambot-dev"))
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
CFG_PATH = DATA_DIR / "config.json"

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("CREATE TABLE IF NOT EXISTS assets (key TEXT PRIMARY KEY, mime TEXT, data BLOB, updated_at TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS asset_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT, filename TEXT, mime TEXT, url TEXT, data BLOB,
                        is_active INTEGER DEFAULT 0, created_at TEXT
                    )""")
        c.commit()

def bootstrap():
    init_db()
    if not CFG_PATH.exists():
        CFG_PATH.write_text(json.dumps({"theme": "default.css"}, indent=2), encoding="utf-8")
    return True

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login", next=request.url))
        return fn(*args, **kwargs)
    return wrapper

def _save_asset(category: str, local_path: Path, url: str) -> str:
    mime = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"
    raw = local_path.read_bytes()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("REPLACE INTO assets(key, mime, data, updated_at) VALUES (?,?,?,?)",
                     (category, mime, raw, datetime.utcnow().isoformat()))
        conn.execute("UPDATE asset_history SET is_active=0 WHERE category=?", (category,))
        conn.execute("""INSERT INTO asset_history(category, filename, mime, url, data, is_active, created_at)
                        VALUES (?,?,?,?,?,1,?)""", (category, local_path.name, mime, url, raw, datetime.utcnow().isoformat()))
        conn.commit()
    socketio.emit("asset_updated", {"category": category, "url": url}, broadcast=True)
    return url

def _theme_name() -> str:
    if CFG_PATH.exists():
        try:
            cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
            return cfg.get("theme", "default.css")
        except Exception:
            pass
    return "default.css"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user", "")
        pw = request.form.get("pass", "")
        user_env = os.getenv("SUPER_ADMIN_USER", "admin")
        pass_env = os.getenv("SUPER_ADMIN_PASS", os.getenv("SUPER_ADMIN_PASSWORD", "admin"))
        if user == user_env and pw == pass_env:
            session["admin"] = user
            return redirect(request.args.get("next") or url_for("dashboard"))
        return render_template("login.html", error="Kredensial salah.")
    return render_template("login.html", error=None)

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/")
def index():
    if session.get("oauth") or session.get("discord_user"):
        return redirect(url_for("servers"))
    return redirect(url_for("dashboard") if session.get("admin") else url_for("login"))
@app.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.get("/settings")
@login_required
def settings():
    return render_template("settings.html")

@app.get("/servers")
@login_required
def servers():
    return render_template("servers.html")

@app.get("/theme")
@login_required
def get_theme():
    return jsonify({"ok": True, "theme": _theme_name(), "path": f"/static/themes/{_theme_name()}"})

@app.get("/theme/list")
@login_required
def list_themes():
    tdir = BASE_DIR / "static" / "themes"
    themes = [p.name for p in tdir.glob("*.css")] if tdir.exists() else ["default.css"]
    return jsonify({"ok": True, "themes": themes})

@app.get("/theme/apply")
@login_required
def apply_theme():
    name = request.args.get("set", "default.css")
    tfile = BASE_DIR / "static" / "themes" / name
    if not name.endswith(".css") or not tfile.exists():
        return jsonify({"ok": False, "error": "not_found"}), 404
    CFG_PATH.write_text(json.dumps({"theme": name}, indent=2), encoding="utf-8")
    socketio.emit("theme_changed", {"theme": name, "path": f"/static/themes/{name}"}, broadcast=True)
    return jsonify({"ok": True})

@app.post("/upload/background")
@login_required
def upload_background():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no_file"}), 400
    f = request.files["file"]
    filename = secure_filename(f.filename or "background")
    updir = BASE_DIR / "static" / "uploads" / "backgrounds"
    updir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_path = updir / f"{ts}_{filename}"
    f.save(local_path)
    rel = str(local_path.relative_to(BASE_DIR))
    url = "/" + rel.replace("\\\\", "/")
    final = _save_asset("background", local_path, url)
    return jsonify({"ok": True, "url": final})

@app.post("/upload/logo")
@login_required
def upload_logo():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "no_file"}), 400
    f = request.files["file"]
    filename = secure_filename(f.filename or "logo")
    updir = BASE_DIR / "static" / "uploads" / "logos"
    updir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    local_path = updir / f"{ts}_{filename}"
    f.save(local_path)
    rel = str(local_path.relative_to(BASE_DIR))
    url = "/" + rel.replace("\\\\", "/")
    final = _save_asset("logo", local_path, url)
    return jsonify({"ok": True, "url": final})


@app.get('/healthz')
def healthz():
    return 'ok', 200


@app.route("/ping", methods=["GET","HEAD"])
def ping():
    return "pong", 200
