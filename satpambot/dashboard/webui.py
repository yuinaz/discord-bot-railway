
from __future__ import annotations
import os, time, json
from pathlib import Path
from flask import (
    Blueprint, current_app, render_template, jsonify, request,
    redirect, send_from_directory
)

# ------------------------------------------------------------------
# UI Config helper
# ------------------------------------------------------------------
class _Cfg:
    def __init__(self):
        self.theme = "gtake"
        self.logo = None
        self.bg_url = None
    def to_dict(self):
        return {"theme": self.theme, "logo": self.logo, "bg_url": self.bg_url}

def _load_ui_local():
    candidates = [
        Path(__file__).with_name("ui_local.json"),
        Path(__file__).parent / "ui_local.json"
    ]
    cfg = _Cfg()
    for c in candidates:
        try:
            if c.exists():
                data = json.loads(c.read_text("utf-8"))
                if isinstance(data, dict):
                    cfg.theme = data.get("theme", cfg.theme)
                    cfg.logo = data.get("logo", cfg.logo)
                    cfg.bg_url = data.get("bg_url", cfg.bg_url)
        except Exception:
            pass
    # Env override
    cfg.theme = os.getenv("UI_THEME", cfg.theme)
    return cfg

# ------------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------------
bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard-static",
)

def register_webui_builtin(app):
    """Call this from app factory to enable the dashboard."""
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    if "dashboard" not in app.blueprints:
        app.register_blueprint(bp)
    return bp

# ------------------------------------------------------------------
# ctx: inject cfg to all templates (so {{cfg.theme}} works)
# ------------------------------------------------------------------
@bp.app_context_processor
def _inject_cfg():
    cfg = _load_ui_local()
    try:
        q_theme = request.args.get("theme")
        if q_theme:
            cfg.theme = q_theme
    except Exception:
        pass
    return {"cfg": cfg}

# ------------------------------------------------------------------
# Theme asset
# ------------------------------------------------------------------
@bp.get("/dashboard-theme/<theme>/theme.css")
def theme_css(theme):
    root = Path(__file__).parent / "themes" / theme / "static"
    f = root / "theme.css"
    if not f.exists():
        return ("/* theme not found */", 200, {"Content-Type": "text/css"})
    return send_from_directory(str(root), "theme.css")

# ------------------------------------------------------------------
# Auth (mock) + navigation
# ------------------------------------------------------------------
@bp.get("/dashboard/login")
def login_page():
    return render_template("login.html", title="Login")

@bp.post("/dashboard/login")
def login_post():
    res = redirect("/dashboard/")
    res.set_cookie("sess", "ok", max_age=86400, httponly=True, samesite="Lax")
    return res

@bp.get("/dashboard/logout")
def dashboard_logout():
    res = redirect("/dashboard/login")
    res.delete_cookie("sess")
    return res

@bp.get("/logout")
def logout_plain():
    return ("OK", 200)

@bp.get("/")
def root_alias():
    return redirect("/dashboard", code=302)

# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------
@bp.get("/dashboard/")
@bp.get("/dashboard")
def dashboard_home():
    return render_template("dashboard.html", title="Dashboard")

@bp.get("/dashboard/settings")
def dashboard_settings():
    return render_template("settings.html", title="Settings")

@bp.get("/dashboard/security")
def dashboard_security():
    # Render template; fallback inline with drag & drop markers if template fails
    try:
        return render_template("security.html", title="Security")
    except Exception:
        return ("""
<!doctype html>
<title>Security</title>
<div class="card neo">
  <h3>Security • Phishing Image Hash</h3>
  <div id="sec-dropzone" class="dropzone sec-dropzone" data-dropzone="security" data-test="dragdrop"
       style="border:2px dashed #889; padding:18px; border-radius:12px; background:rgba(255,255,255,0.02)">
    <strong>Drag &amp; Drop files here</strong>
  </div>
  <div style="margin-top:10px;opacity:.8">
    Signatures tersimpan: <b id="phash-count">0</b>
  </div>
</div>
""", 200, {"Content-Type":"text/html; charset=utf-8"})

# ------------------------------------------------------------------
# Upload handlers (drag & drop targets) + static uploads
# ------------------------------------------------------------------
def _uploads_dir():
    d = Path(__file__).with_name("static") / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _save_files_from_request(files):
    saved = []
    for f in files or []:
        if not getattr(f, "filename", ""):
            continue
        name = f"{int(time.time())}_{f.filename.replace(' ', '_')}"
        path = _uploads_dir() / name
        f.save(path)
        saved.append({"name": name, "url": f"/dashboard-static/uploads/{name}"})
    return saved

@bp.post("/dashboard/upload")
def upload_dashboard():
    files = request.files.getlist("file")
    saved = _save_files_from_request(files)
    return jsonify({"ok": True, "files": saved})

@bp.post("/dashboard/security/upload")
def upload_security():
    files = request.files.getlist("file")
    saved = _save_files_from_request(files)
    return jsonify({"ok": True, "files": saved})

@bp.get("/dashboard-static/uploads/<path:fname>")
def static_uploads(fname):
    return send_from_directory(str(_uploads_dir()), fname)

# ------------------------------------------------------------------
# Fallback APIs (if app-level routes are absent)
# ------------------------------------------------------------------
@bp.get("/dashboard/api/metrics")
def api_metrics_fallback():
    # Try app-level /api/live/stats if available
    try:
        v = current_app.view_functions.get("api_live_stats")
        if v:
            return v()
    except Exception:
        pass
    return jsonify({"guilds":0,"members":0,"channels":0,"threads":0,"online":0,"latency_ms":0,"updated":int(time.time())})

@bp.get("/dashboard/api/bans")
def api_bans_fallback():
    cands = [
        Path("data/mod/ban_log.json"),
        Path("data/ban_log.json"),
        Path("data/mod/bans.json"),
    ]
    recs = []
    for p in cands:
        try:
            if p.exists():
                data = json.loads(p.read_text("utf-8"))
                if isinstance(data, dict) and "items" in data: data = data["items"]
                if isinstance(data, list): recs.extend(data)
        except Exception:
            pass
    lim = int(request.args.get("limit") or 10)
    out = []
    for x in recs[-lim:]:
        user = x.get("user") or x.get("username") or x.get("tag") or ""
        uid  = x.get("user_id") or x.get("id")
        when = x.get("when") or ""
        out.append({"user": user, "user_id": uid, "when_str": when})
    return jsonify(out)
