from __future__ import annotations
import os, json, time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from flask_socketio import SocketIO

load_dotenv()

MOD_DIR = Path(__file__).resolve().parent
DASH_DIR = MOD_DIR
DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(DASH_DIR / "templates"),
    static_folder=str(DASH_DIR / "static"),
    static_url_path="/static",
)
app.secret_key = os.getenv("FLASK_SECRET", "satpambot-secret")
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
# Extend Jinja loader to include other template roots (root /templates & editor/templates)
from jinja2 import ChoiceLoader, FileSystemLoader
try:
    extra_loaders = [
        FileSystemLoader(str((Path(__file__).resolve().parents[2] / "bot" / "modules" / "editor" / "templates"))),
        FileSystemLoader(str(Path().resolve() / "templates")),
    ]
    app.jinja_loader = ChoiceLoader([app.jinja_loader, *extra_loaders])
except Exception:
    pass


@app.route("/static/<path:filename>")
def _static(filename):
    return send_from_directory(app.static_folder, filename)

@app.get("/healthz")
def healthz():
    return jsonify(ok=True, status="alive")

@app.get("/")
def root():
    # Dashboard home: jika belum login → ke /login, kalau sudah → render dashboard.html
    try:
        if not session.get("auth"):
            return redirect(url_for("login_page"))
    except Exception:
        pass
    return render_template("dashboard.html")

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



from flask import request, jsonify, send_from_directory
import os, json, time
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

UI_CFG = DATA_DIR / "ui_config.json"

def _load_ui():
    if UI_CFG.exists():
        try:
            return json.loads(UI_CFG.read_text('utf-8'))
        except Exception:
            return {}
    return {}

def _save_ui(d):
    UI_CFG.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

@app.get("/api/ui-config")
def api_ui_get():
    return jsonify(_load_ui())

@app.post("/api/ui-config")
def api_ui_set():
    d = _load_ui()
    body = request.get_json(silent=True) or {}
    d.update({k:v for k,v in body.items() if k in ("theme","accent_color","background_mode","background_url","apply_to_login")})
    _save_ui(d)
    return jsonify({"ok":True, "cfg": d})

@app.post("/api/upload/background")
def api_upload_bg():
    f = request.files.get('file')
    if not f: return jsonify({"ok":False,"error":"no file"}), 400
    name = f"bg_{int(time.time())}_{f.filename.replace(' ','_')}"
    path = UPLOAD_DIR / name
    f.save(str(path))
    url = f"/uploads/{name}"
    d = _load_ui(); d["background_url"] = url
    _save_ui(d)
    return jsonify({"ok":True,"url":url})

@app.get("/uploads/<path:filename>")
def uploaded_files(filename):
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.get("/api/metrics")
def api_metrics():
    # lightweight metrics (no psutil hard dependency)
    try:
        import psutil, os
        mem = psutil.Process(os.getpid()).memory_info().rss/1024/1024
        cpu = psutil.cpu_percent(interval=0.05)
    except Exception:
        mem, cpu = 0, 0
    start = getattr(app, "start_ts", None) or int(time.time())
    if not getattr(app, "start_ts", None):
        app.start_ts = start
    up = int(time.time()-start)
    return jsonify({"uptime": up, "cpu": cpu, "mem_mb": mem, "servers":[
        {"name":"Local Web (127.0.0.1:8080)","status":"DOWN","ping_ms":1},
        {"name":"Discord API","status":"UP","ping_ms":5},
    ]})



from flask import render_template, redirect, url_for, request, jsonify, send_from_directory
import time, os, json
from pathlib import Path

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UI_CFG = DATA_DIR / "ui_config.json"

def _load_ui():
    try:
        return json.loads(UI_CFG.read_text('utf-8')) if UI_CFG.exists() else {}
    except Exception:
        return {}
def _save_ui(d):
    UI_CFG.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

@app.get("/dashboard")
def dash_home():
    return render_template("dashboard.html")

@app.get("/dashboard/settings")
def dash_settings():
    return render_template("settings.html")

@app.get("/settings")
def alias_settings():
    return redirect(url_for('dash_settings'))

@app.get("/dashboard-static/<path:filename>")
def dash_static(filename):
    return send_from_directory(str(Path(__file__).parent / "static"), filename)

@app.get("/api/ui-config")
def api_ui_get():
    return jsonify(_load_ui())

@app.post("/api/ui-config")
def api_ui_set():
    d = _load_ui()
    body = request.get_json(silent=True) or {}
    for k in ("logo_url","theme","accent_color","background_mode","background_url","apply_to_login"):
        if k in body: d[k] = body[k]
    _save_ui(d); return jsonify({"ok":True,"cfg":d})

@app.post("/api/upload/background")
def api_upload_bg():
    f = request.files.get('file')
    if not f: return jsonify({"ok":False,"error":"no file"}), 400
    name = f"bg_{int(time.time())}_{f.filename.replace(' ','_')}"
    path = UPLOAD_DIR / name; f.save(str(path))
    url = f"/uploads/{name}"
    d = _load_ui(); d["background_url"] = url; _save_ui(d)
    return jsonify({"ok":True,"url":url})

@app.get("/uploads/<path:filename>")
def uploaded_files(filename): return send_from_directory(str(UPLOAD_DIR), filename)

@app.get("/api/metrics")
def api_metrics():
    series = {"total":[1,2,3,4,6,8,9,11,13,14], "lat":[110,90,120,80,70,95,88,92,86,90], "up":[1,1,1,1,1,1,1,1,1,1], "g":[1,1,1,1,1,1,1,1,1,1]}
    try:
        import psutil, os as _os
        mem = psutil.Process(_os.getpid()).memory_info().rss/1024/1024
        cpu = psutil.cpu_percent(interval=0.05)
    except Exception:
        mem, cpu = 0, 0
    start = int(getattr(app, 'start_ts', time.time())); 
    if not getattr(app, 'start_ts', None): app.start_ts = start
    servers=[{"name":"Local Web (127.0.0.1:8080)","status":"DOWN","ping_ms":1}]
    ping_ms = None
    try:
        import requests
        t0=time.time(); requests.get("https://discord.com/api/v10/gateway", timeout=2)
        ping_ms=int((time.time()-t0)*1000); servers.append({"name":"Discord API","status":"UP","ping_ms":ping_ms})
    except Exception:
        servers.append({"name":"Discord API","status":"DOWN","ping_ms":None})
    return jsonify({"uptime":int(time.time()-start),"cpu":cpu,"mem_mb":mem,"servers":servers,"series":series,"guilds":1,"latency_ms":ping_ms,"total_msgs":0})
