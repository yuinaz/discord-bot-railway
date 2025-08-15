
import os
import json
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "satpambot-dev")
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
CFG_PATH = DATA_DIR / "config.json"

# === Discord OAuth & Remote Bot Bridge (added) ===
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "").strip()
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "").strip()
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "").strip()  # e.g. https://satpambot-dashboard.onrender.com/callback
BOT_BASE_URL = os.getenv("BOT_BASE_URL", "").rstrip("/")          # e.g. https://satpambot-n0c2.onrender.com
SHARED_DASH_TOKEN = os.getenv("SHARED_DASH_TOKEN", "")            # MUST match bot service

DISCORD_API = "https://discord.com/api/v10"

def _hmac_headers(method: str, path: str, body: str = ""):
    ts = str(int(time.time()))
    raw = (method + "\n" + path + "\n" + body + "\n" + ts).encode("utf-8")
    sig = hmac.new(SHARED_DASH_TOKEN.encode("utf-8"), raw, hashlib.sha256).hexdigest() if SHARED_DASH_TOKEN else ""
    h = {"Content-Type": "application/json"}
    if SHARED_DASH_TOKEN:
        h.update({"X-Auth": f"Bearer {SHARED_DASH_TOKEN}", "X-Sign": sig, "X-Ts": ts})
    return h

def _bot_get(path: str):
    url = BOT_BASE_URL + path
    return requests.get(url, headers=_hmac_headers("GET", path, ""), timeout=10)

def _bot_post(path: str, payload: dict):
    import json as _json
    body = _json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    url = BOT_BASE_URL + path
    return requests.post(url, headers=_hmac_headers("POST", path, body), data=body.encode("utf-8"), timeout=10)

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
        if user == os.getenv("SUPER_ADMIN_USER", "admin") and pw == os.getenv("SUPER_ADMIN_PASSWORD", "admin"):
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


# === OAuth routes (added) ===
@app.get("/discord/login")
def discord_login():
    if not (DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET and OAUTH_REDIRECT_URI):
        return "Discord OAuth belum dikonfigurasi (set DISCORD_CLIENT_ID/DISCORD_CLIENT_SECRET/OAUTH_REDIRECT_URI).", 500
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds",
        "prompt": "none",
    }
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return redirect(f"https://discord.com/api/oauth2/authorize?{qs}")

@app.get("/callback")
def discord_callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": OAUTH_REDIRECT_URI,
    }
    r = requests.post(f"{DISCORD_API}/oauth2/token", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
    if r.status_code != 200:
        return f"Token exchange failed: {r.status_code} {r.text}", 400
    tok = r.json()
    session["oauth"] = tok
    # fetch user + guilds
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    u = requests.get(f"{DISCORD_API}/users/@me", headers=h, timeout=10).json()
    g = requests.get(f"{DISCORD_API}/users/@me/guilds", headers=h, timeout=10).json()
    session["discord_user"] = u
    session["discord_guilds"] = g
    return redirect(url_for("servers"))

# === Remote bot APIs (added) ===
@app.get("/api/guilds")
def api_guilds():
    # requires Discord login to know manageable guilds; fallback to admin session
    guilds = session.get("discord_guilds", [])
    try:
        bot_ids = set(_bot_get("/internal/api/guilds").json())
    except Exception:
        bot_ids = set()
    out = []
    for g in guilds:
        gid = str(g.get("id"))
        # MANAGE_GUILD (0x20) or ADMIN (0x8)
        try:
            perms = int(g.get("permissions", "0"))
        except Exception:
            perms = 0
        manageable = (perms & 0x20) != 0 or (perms & 0x8) != 0
        out.append({
            "id": gid,
            "name": g.get("name"),
            "system_channel_id": g.get("system_channel_id"),
            "manageable": manageable,
            "bot_present": gid in bot_ids,
        })
    return jsonify({"ok": True, "data": out})

@app.get("/api/guilds/<gid>/status")
def api_guild_status(gid: str):
    r = _bot_get(f"/internal/api/guilds/{gid}/status")
    return (r.text, r.status_code, {"Content-Type":"application/json"})

@app.post("/api/guilds/<gid>/say")
def api_guild_say(gid: str):
    payload = request.get_json(silent=True) or {}
    r = _bot_post(f"/internal/api/guilds/{gid}/say", payload)
    return (r.text, r.status_code, {"Content-Type":"application/json"})

@app.get('/healthz')
def healthz():
    return 'ok', 200