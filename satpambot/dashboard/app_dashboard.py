from __future__ import annotations
import os, json, time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_socketio import SocketIO

load_dotenv()

MOD_DIR = Path(__file__).resolve().parent
DASH_DIR = MOD_DIR
DATA_DIR = Path("data")

app = Flask(
    __name__,
    template_folder=str(DASH_DIR / "templates"),
    static_folder=str(DASH_DIR / "static"),
    static_url_path="/static",
)
app.secret_key = os.getenv("FLASK_SECRET", "satpambot-secret")
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

@app.route("/static/<path:filename>")
def _static(filename):
    return send_from_directory(app.static_folder, filename)

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, status="alive")

@app.get("/")
def root():
    return "OK", 200

def _admin_creds():
    user = os.getenv("ADMIN_USERNAME") or os.getenv("ADMIN_USER") or os.getenv("ADMIN") or "admin"
    pwd  = os.getenv("ADMIN_PASSWORD") or os.getenv("ADMIN_PASS") or os.getenv("PASSWORD") or ""
    return user, pwd

@app.context_processor
def inject_theme_path():
    theme = None
    try:
        theme = session.get("theme_css")
    except Exception:
        pass
    if not theme:
        theme = "/static/themes/dark.css"
    return {"theme_path": theme}

UI_CFG_PATH = DATA_DIR / "ui_config.json"
def _ui_cfg_load():
    try: return json.load(open(UI_CFG_PATH, "r", encoding="utf-8"))
    except Exception: return {}
def _ui_cfg_save(cfg: dict):
    UI_CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(UI_CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

@app.context_processor
def inject_login_ui():
    cfg = _ui_cfg_load()
    return {
        "login_logo": cfg.get("login_logo") or "/static/img/login-user.svg",
        "login_bg": cfg.get("login_bg") or "linear-gradient(120deg,#f093fb 0%,#f5576c 100%)",
        "login_particles": bool(cfg.get("login_particles", True)),
    }

@app.get("/api/ui-config")
def api_ui_cfg_get():
    return _ui_cfg_load()

@app.post("/api/ui-config")
def api_ui_cfg_post():
    data = request.get_json(silent=True) or {}
    cfg = _ui_cfg_load()
    if "login_logo" in data: cfg["login_logo"] = str(data["login_logo"]).strip()
    if "login_bg" in data:   cfg["login_bg"]   = str(data["login_bg"]).strip()
    if "login_particles" in data: cfg["login_particles"] = bool(data["login_particles"])
    _ui_cfg_save(cfg); return {"ok": True, **cfg}

WL_PATH = DATA_DIR / "whitelist_domains.json"
def _wl_load():
    try: return json.load(open(WL_PATH, "r", encoding="utf-8"))
    except Exception: return []
def _wl_save(domains):
    WL_PATH.parent.mkdir(parents=True, exist_ok=True)
    norm = sorted({(d or "").strip().lower() for d in (domains or []) if (d or "").strip()})
    json.dump(norm, open(WL_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return norm

@app.get("/api/whitelist")
def api_whitelist_get():
    return {"domains": _wl_load()}

@app.post("/api/whitelist")
def api_whitelist_post():
    data = request.get_json(silent=True) or {}
    if "text" in data and isinstance(data["text"], str):
        return {"ok": True, "domains": _wl_save([ln.strip() for ln in data["text"].splitlines()])}
    if "domains" in data and isinstance(data["domains"], list):
        return {"ok": True, "domains": _wl_save(data["domains"])}
    return {"ok": False, "error": "invalid payload"}, 400

PHISH_CONFIG_PATH = DATA_DIR / "phish_config.json"
def _cfg_load():
    try: return json.load(open(PHISH_CONFIG_PATH, "r", encoding="utf-8"))
    except Exception: return {"autoban": False, "threshold": 8, "log_thread_name": "Ban Log"}
def _cfg_save(cfg: dict):
    PHISH_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(PHISH_CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

@app.get("/api/phish-config")
def api_phish_cfg_get():
    return _cfg_load()

@app.post("/api/phish-config")
def api_phish_cfg_post():
    data = request.get_json(silent=True) or {}
    cfg = _cfg_load()
    if "autoban" in data: cfg["autoban"] = bool(data["autoban"])
    if "threshold" in data:
        try: cfg["threshold"] = max(1, min(16, int(data["threshold"])))
        except Exception: pass
    if "log_thread_name" in data:
        cfg["log_thread_name"] = (str(data["log_thread_name"]).strip() or "Ban Log")
    _cfg_save(cfg); return {"ok": True, **cfg}

RECENT_BANS_PATH = DATA_DIR / "recent_bans.json"
def _recent_bans_load():
    try: return json.load(open(RECENT_BANS_PATH, "r", encoding="utf-8"))
    except Exception: return {"items": []}

@app.get("/api/recent-bans")
def api_recent_bans():
    data = _recent_bans_load()
    items = sorted(data.get("items", []), key=lambda x: x.get("ts", 0), reverse=True)[:50]
    return {"items": items, "ts": int(time.time())}

@app.get("/login")
def login_page():
    return render_template("login.html")

@app.post("/login")
def login_post():
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    admin_u, admin_p = _admin_creds()
    if u == admin_u and p == admin_p:
        session["auth"] = True
        return redirect(url_for("root"))
    return "Invalid credentials", 401
