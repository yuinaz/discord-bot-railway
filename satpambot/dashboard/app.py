
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


@app.route("/ping", methods=["GET","HEAD"])
def ping():
    return "pong", 200

from flask import redirect

@app.route('/assets/<path:filename>')
def _assets(filename):
    return _sfd(_ASSETS_DIR, filename)


# --- admin fallback integration ---
import os
try:
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key')
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = bool(os.getenv('SESSION_COOKIE_SECURE','1')!='0')
except Exception:
    pass
try:
    from .admin_fallback import admin_fallback_bp
except Exception:
    from .admin_fallback import admin_fallback_bp
try:
    app.register_blueprint(admin_fallback_bp)
except Exception:
    pass

# Aliases so these URLs always work
from flask import redirect








try:
    from flask import redirect
    # Root -> /login jika belum ada rule '/'
    if not any(getattr(r, "rule", None) == "/" for r in app.url_map.iter_rules()):
        @app.route("/")
        def __root_redirect_to_login():
            return redirect("/login", code=302)
    # /discord/login -> /login jika belum ada rule '/discord/login'
    if not any(getattr(r, "rule", None) == "/discord/login" for r in app.url_map.iter_rules()):
        @app.route("/discord/login")
        def __discord_login_redirect_to_login():
            return redirect("/login", code=302)
except Exception:
    pass


# --- force alias to /login (safe; runs before routes) ---
try:
    from flask import request, redirect
    @app.before_request
    def _force_login_alias():
        if request.path in ("/", "/discord/login"):
            return redirect("/login", code=302)
except Exception:
    pass


# --- hard override: force /login to use admin_fallback, plus aliases ---
try:
    from flask import request, redirect
    from .admin_fallback import admin_login  # form user/pass (ENV)
    @app.before_request
    def _login_overrides():
        # Aliases menuju /login
        if request.path in ("/", "/discord/login"):
            return redirect("/login", code=302)
        # Paksa /login selalu pakai admin_fallback (hindari handler lama "Invalid request!")
        if request.path == "/login" and request.method in ("GET","POST"):
            return admin_login()
except Exception:
    pass


# --- API fallback saat bot OFF (dipasang hanya kalau route belum ada) ---
try:
    import os
    from flask import jsonify
    # /api/live
    if not any(getattr(r, "rule", None) == "/api/live" for r in app.url_map.iter_rules()):
        @app.get("/api/live")
        def __api_live_fallback():
            return jsonify(ok=True, live=True, bot="off", env=os.getenv("ENV","local")), 200
    # /api/ping
    if not any(getattr(r, "rule", None) == "/api/ping" for r in app.url_map.iter_rules()):
        @app.get("/api/ping")
        def __api_ping_fallback():
            return jsonify(ok=True, pong=True), 200
except Exception:
    pass


# --- quiet access log for health/ping routes & lightweight endpoints ---
try:
    import logging
    from flask import request, jsonify

    _QUIET_PATHS = {"/ping", "/healthz", "/api/ping", "/api/live"}

    @app.before_request
    def __mute_health_accesslog():
        # tandai request agar tidak dilog kalau termasuk quiet paths atau healthcheck UA
        ua = (request.headers.get("User-Agent") or "").lower()
        if request.path in _QUIET_PATHS or "uptimerobot" in ua or "render" in ua:
            # flag khusus yang kita cek di after_request
            request.environ["_suppress_access_log"] = True

    @app.after_request
    def __custom_accesslog(resp):
        # kalau tidak health/ping, tulis access log sederhana via logger 'entry'
        try:
            if not request.environ.get("_suppress_access_log"):
                logging.getLogger("entry").info("%s %s %s", request.method, request.path, resp.status_code)
        except Exception:
            pass
        return resp

    # Sediakan /ping dan /healthz kalau belum ada (HEAD/GET, no body 204)
    if not any(getattr(r, "rule", None) == "/ping" for r in app.url_map.iter_rules()):
        @app.route("/ping", methods=["GET","HEAD"])
        def __ping(): return ("", 204)
    if not any(getattr(r, "rule", None) == "/healthz" for r in app.url_map.iter_rules()):
        @app.route("/healthz", methods=["GET","HEAD"])
        def __healthz(): return ("", 204)

    # Fallback API (kalau bot OFF): /api/ping & /api/live
    if not any(getattr(r, "rule", None) == "/api/ping" for r in app.url_map.iter_rules()):
        @app.get("/api/ping")
        def __api_ping_fallback(): return jsonify(ok=True, pong=True), 200
    if not any(getattr(r, "rule", None) == "/api/live" for r in app.url_map.iter_rules()):
        @app.get("/api/live")
        def __api_live_fallback(): return jsonify(ok=True, live=True, bot="off"), 200
except Exception:
    pass

