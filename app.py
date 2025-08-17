# satpambot/dashboard/app.py
from __future__ import annotations

import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, session,
    send_from_directory, jsonify
)
from flask_socketio import SocketIO

# --- init ------------------------------------------------------------
load_dotenv()

BASE_DIR = Path(__file__).parent
app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static",
)
# secret key untuk session (gunakan ENV jika ada)
app.secret_key = os.getenv("FLASK_SECRET", "satpambot-secret")

# SocketIO (mode threading biar aman di Render tanpa eventlet/gevent)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

# Fallback static route (kadang perlu di Render)
@app.route("/static/<path:filename>")
def _static(filename: str):
    return send_from_directory(app.static_folder, filename)

# Health check + root (biar Render tidak “Deploying” terus)
@app.get("/healthz")
def healthz():
    return jsonify(ok=True, status="alive")

@app.get("/")
def root():
    # boleh dialihkan ke login atau tampil OK sederhana
    return "OK", 200
    # return redirect(url_for("login"))  # kalau sudah ada view login()

# --- helper admin creds ----------------------------------------------
def _admin_creds():
    user = os.getenv("ADMIN_USERNAME") or os.getenv("ADMIN_USER") or os.getenv("ADMIN") or "admin"
    pwd  = os.getenv("ADMIN_PASSWORD") or os.getenv("ADMIN_PASS") or os.getenv("PASSWORD") or ""
    return user, pwd

# --- THEME context ---------------------------------------------------
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

# --- LOGIN UI config (logo/bg/particles) -----------------------------
UI_CFG_PATH = os.path.join("data", "ui_config.json")

def _ui_cfg_load() -> dict:
    try:
        return json.load(open(UI_CFG_PATH, "r", encoding="utf-8"))
    except Exception:
        return {}

def _ui_cfg_save(cfg: dict) -> None:
    os.makedirs(os.path.dirname(UI_CFG_PATH), exist_ok=True)
    json.dump(cfg, open(UI_CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

@app.context_processor
def inject_login_ui():
    cfg = _ui_cfg_load()
    logo = cfg.get("login_logo") or "/static/img/login-user.svg"
    bg   = cfg.get("login_bg") or "linear-gradient(120deg,#f093fb 0%,#f5576c 100%)"
    particles = bool(cfg.get("login_particles", True))
    return {"login_logo": logo, "login_bg": bg, "login_particles": particles}

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
    _ui_cfg_save(cfg)
    return {"ok": True, **cfg}

# --- WHITELIST API ---------------------------------------------------
WL_PATH = os.path.join("data", "whitelist_domains.json")

def _wl_load() -> list[str]:
    try:
        return json.load(open(WL_PATH, "r", encoding="utf-8"))
    except Exception:
        return []

def _wl_save(domains: list[str]) -> list[str]:
    os.makedirs(os.path.dirname(WL_PATH), exist_ok=True)
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
        items = [ln.strip() for ln in data["text"].splitlines()]
        return {"ok": True, "domains": _wl_save(items)}
    if "domains" in data and isinstance(data["domains"], list):
        return {"ok": True, "domains": _wl_save(data["domains"])}
    return {"ok": False, "error": "invalid payload"}, 400

# --- PHISH CONFIG API -----------------------------------------------
PHISH_CONFIG_PATH = os.path.join("data", "phish_config.json")

def _cfg_load() -> dict:
    try:
        return json.load(open(PHISH_CONFIG_PATH, "r", encoding="utf-8"))
    except Exception:
        return {"autoban": False, "threshold": 8, "log_thread_name": "Ban Log"}

def _cfg_save(cfg: dict) -> None:
    os.makedirs(os.path.dirname(PHISH_CONFIG_PATH), exist_ok=True
    )
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
        try:
            v = max(1, min(16, int(data["threshold"])))
            cfg["threshold"] = v
        except Exception:
            pass
    if "log_thread_name" in data:
        name = str(data["log_thread_name"]).strip() or "Ban Log"
        cfg["log_thread_name"] = name
    _cfg_save(cfg)
    return {"ok": True, **cfg}

# --- RECENT BANS (untuk floating widget) -----------------------------
RECENT_BANS_PATH = os.path.join("data", "recent_bans.json")

def _recent_bans_load() -> dict:
    try:
        return json.load(open(RECENT_BANS_PATH, "r", encoding="utf-8"))
    except Exception:
        return {"items": []}

@app.get("/api/recent-bans")
def api_recent_bans():
    data = _recent_bans_load()
    items = sorted(data.get("items", []), key=lambda x: x.get("ts", 0), reverse=True)[:50]
    return {"items": items, "ts": int(time.time())}

# --------------------------------------------------------------------
# Tambahkan route login-mu di bawah ini (jika belum ada). Contoh minimal:
@app.get("/login")
def login_page():
    # render template login.html (sudah ada di templates)
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
