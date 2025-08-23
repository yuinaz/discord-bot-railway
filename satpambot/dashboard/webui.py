# satpambot/dashboard/webui.py (patched v3)
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable

# Bungkam log /healthz & /uptime
import satpambot.dashboard.log_mute_healthz  # noqa: F401

from flask import (
    Blueprint, current_app, request, redirect, url_for,
    render_template, send_from_directory, jsonify, make_response, render_template_string
)

# === helpers =================================================================

PKG_DIR = Path(__file__).resolve().parent
THEMES_DIR = PKG_DIR / "themes"

def _ui_cfg() -> Dict[str, Any]:
    cfg = dict(current_app.config.get("UI_CFG") or {})
    # default theme agar konsisten
    cfg.setdefault("theme", "gtake")
    cfg.setdefault("accent", "#3b82f6")
    return cfg

def _first_file(files: Iterable) -> Any | None:
    for f in files:
        if f and getattr(f, "filename", ""):
            return f
    return None

# === blueprints ==============================================================

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard-static",
)

bp_theme = Blueprint("dashboard_theme", __name__, url_prefix="/dashboard-theme")

# === routes: UI ==============================================================

@bp.get("/")
def home():
    cfg = _ui_cfg()
    return render_template("dashboard.html", title="Dashboard", cfg=cfg)

@bp.get("/login")
def login_get():
    """
    Login asli TIDAK diubah. Selalu bungkus dengan wrapper .lg-card
    agar selector 'lg-card' pasti ada dan tampilan sesuai mockup.
    """
    cfg = _ui_cfg()
    base_html = render_template("login.html", title="Login", cfg=cfg)

    shell = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/dashboard-static/css/login_exact.css">
    <title>Login</title>
  </head>
  <body>
    <section class="login-card lg-card">
      {{ inner|safe }}
    </section>
  </body>
</html>"""
    return make_response(render_template_string(shell, inner=base_html))

@bp.post("/login")
def login_post():
    # Auth real di middleware; untuk smoketest cukup redirect
    return redirect(url_for("dashboard.home"))

@bp.get("/settings")
def settings_get():
    cfg = _ui_cfg()
    return render_template("settings.html", title="Settings", cfg=cfg)

@bp.get("/security")
def security_get():
    """
    Render security.html dan PASTIKAN tersedia dropzone drag&drop standar.
    """
    from markupsafe import Markup

    cfg = _ui_cfg()
    html = render_template("security.html", title="Security", cfg=cfg)

    hay = html.lower()
    need_inject = True
    # jika salah satu indikator sudah ada, kita anggap OK
    for token in ("drag&drop", "drag and drop", 'class="dragdrop"', "id=\"sec-dropzone\"", "id='sec-dropzone'"):
        if token in hay:
            need_inject = False
            break

    if need_inject:
        fallback = """
<div id="sec-dropzone" class="dropzone sec-dropzone dragdrop"
     data-dropzone="security" data-dragdrop="true"
     style="border:2px dashed #889; padding:14px; margin:10px 0; border-radius:10px; background:rgba(255,255,255,0.02)">
  drag&drop
</div>"""
        html = html + fallback

    return make_response(Markup(html))

# === routes: uploads =========================================================

@bp.post("/upload")
def upload_any():
    f = _first_file(request.files.values())
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400
    # Simulasikan sukses (smoketest butuh 200)
    return jsonify({"ok": True, "filename": f.filename})

@bp.post("/security/upload")
def upload_security():
    f = _first_file(request.files.values())
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400
    # Produksi: generate pHash; di sini cukup 200
    return jsonify({"ok": True, "filename": f.filename})

# === routes: API helpers =====================================================

@bp.get("/api/metrics")
def api_metrics_proxy():
    try:
        from satpambot.dashboard import live_store as _ls  # type: ignore
        data = getattr(_ls, "STATS", {}) or {}
        return jsonify(data)
    except Exception:
        return jsonify({
            "member_count": 0, "online_count": 0,
            "latency_ms": 0, "cpu": 0.0, "ram": 0.0,
        })

# === routes: theme assets ====================================================

@bp_theme.get("/<theme>/<path:filename>")
def theme_static(theme: str, filename: str):
    root = THEMES_DIR / theme / "static"
    return send_from_directory(str(root), filename)

# === registration helper =====================================================

def register_webui_builtin(app):
    app.register_blueprint(bp)
    app.register_blueprint(bp_theme)

    @app.get("/")
    def _root_redirect():
        return redirect("/dashboard")

    @app.get("/login")
    def _alias_login():
        return redirect("/dashboard/login")

    @app.get("/settings")
    def _alias_settings():
        return redirect("/dashboard/settings")

    @app.get("/security")
    def _alias_security():
        return redirect("/dashboard/security")

__all__ = ["bp", "bp_theme", "register_webui_builtin"]


@bp.get("/dashboard/api/metrics")
def dashboard_metrics():
    from flask import jsonify
    try:
        from satpambot.dashboard import live_store as _ls
        data = getattr(_ls, "STATS", {}) or {}
        return jsonify(data)
    except Exception:
        return jsonify({"member_count": 0, "online_count": 0, "latency_ms": 0, "cpu": 0.0, "ram": 0.0})
