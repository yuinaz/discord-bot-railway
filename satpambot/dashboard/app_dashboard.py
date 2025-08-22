# -*- coding: utf-8 -*-
"""
SatpamBot Dashboard (final)
- UI config (theme/accent/bg/logo)
- Upload background & logo (file)
- Theme discovery (static/themes/*.css + data/themes/*.json)
- Live summary endpoints (fallback-safe)
- Healthz & uptime
- Pages: /login, /dashboard, /dashboard/settings
"""
from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Dict, Any
from flask import (
    Flask, jsonify, request, send_from_directory, Blueprint,
    render_template, redirect, url_for, session
)
from werkzeug.utils import secure_filename

import logging

def _install_health_log_filter():
    try:
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                # Hide access logs for health endpoints
                return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        # Never crash on logging setup
        pass

# ------------------------------------------------------------------------------
# Paths & storage
# ------------------------------------------------------------------------------
APP_ROOT   = Path(__file__).resolve().parent
TEMPLATES  = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

DATA_DIR   = Path("data")
UPLOAD_DIR = DATA_DIR / "uploads"
THEMES_DIR = DATA_DIR / "themes"         # custom JSON themes (opsional)
LIVE_PATH  = DATA_DIR / "live.json"      # di-update oleh bot (opsional)
PRESENCE_PATH = DATA_DIR / "presence.json"

for p in (DATA_DIR, UPLOAD_DIR, THEMES_DIR):
    p.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / "ui_config.json"
DEFAULT_CONFIG: Dict[str, Any] = {
    "theme": "Dark",
    "accent": "#2563eb",
    "bg_mode": "None",     # None | Image | Particles | Video
    "bg_url": "",
    "apply_login": False,
    "logo_url": ""
}

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------
def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def _save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def _themes_builtin() -> list[str]:
    # daftar default + yang ada di /static/themes/*.css
    names = {"Dark", "Light", "Nord", "Dracula", "Ocean", "Forest", "Aurora", "Neo", "Solar", "Monokai"}
    themes_css = (STATIC_DIR / "themes")
    if themes_css.exists():
        for css in themes_css.glob("*.css"):
            names.add(css.stem)
    return sorted(names)

def _themes_custom() -> list[str]:
    # custom JSON themes yg kamu taruh di data/themes/*.json
    names = []
    if THEMES_DIR.exists():
        for p in THEMES_DIR.glob("*.json"):
            names.append(p.stem)
    return sorted(set(names))

def _safe_live_json() -> Dict[str, Any]:
    """Baca live metric dari file, fallback 0 kalau belum ada."""
    for p in (LIVE_PATH, PRESENCE_PATH):
        if p.exists():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    return raw
            except Exception:
                pass
    return {
        "guilds": 0, "members": 0, "channels": 0, "threads": 0,
        "online": 0, "latency_ms": 0, "ts": int(time.time())
    }

# ------------------------------------------------------------------------------
# App factory
# ------------------------------------------------------------------------------
def create_app() -> Flask:
    app = Flask(
        "satpambot_dashboard",
        template_folder=str(TEMPLATES),
        static_folder=None
    )
    app.secret_key = os.getenv("FLASK_SECRET", "satpambot-secret")  # untuk session login

    # Static blueprint (akses dengan url_for('dashboard_static.static', filename='...'))
    static_bp = Blueprint("dashboard_static", __name__, static_folder=str(STATIC_DIR))
    app.register_blueprint(static_bp, url_prefix="/dashboard-static")

    # Upload served from /uploads/*
    @app.route("/uploads/<path:filename>")
    def uploads(filename: str):
        return send_from_directory(str(UPLOAD_DIR), filename, conditional=True)

    # --------------------------- UI Config API -------------------------------
    @app.get("/api/ui-config")
    def api_get_ui_config():
        cfg = _load_config()
        return jsonify({
            "theme": cfg.get("theme"),
            "accent": cfg.get("accent"),
            "bg_mode": cfg.get("bg_mode"),
            "bg_url": cfg.get("bg_url"),
            "apply_login": bool(cfg.get("apply_login")),
            "logo_url": cfg.get("logo_url", "")
        })

    @app.post("/api/ui-config")
    def api_post_ui_config():
        payload = request.get_json(force=True, silent=True) or {}
        cfg = _load_config()

        theme = payload.get("theme") or payload.get("Theme") or payload.get("theme_name")
        if theme: cfg["theme"] = str(theme)

        accent = payload.get("accent") or payload.get("accent_color")
        if accent: cfg["accent"] = str(accent)

        bg_mode = payload.get("bg_mode") or payload.get("background_mode")
        if bg_mode: cfg["bg_mode"] = str(bg_mode)

        bg_url = payload.get("bg_url") or payload.get("background_url")
        if bg_url is not None: cfg["bg_url"] = str(bg_url)

        apply_login = payload.get("apply_login") or payload.get("apply_to_login")
        if apply_login is not None: cfg["apply_login"] = bool(apply_login)

        logo_url = payload.get("logo_url")
        if logo_url is not None: cfg["logo_url"] = str(logo_url)

        _save_config(cfg)
        return jsonify({"ok": True, "config": cfg})

    @app.get("/api/themes")
    def api_themes():
        all_names = list(dict.fromkeys(_themes_builtin() + _themes_custom()))
        return jsonify({"themes": all_names, "count": len(all_names)})

    # ---------------------- Uploads (Background & Logo) ----------------------
    @app.post("/api/upload/background")
    def api_upload_background():
        f = request.files.get("file")
        if not f:
            return jsonify({"ok": False, "error": "no file"}), 400
        ts = time.strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(f.filename or "")[1] or ".jpg"
        out = UPLOAD_DIR / f"bg_{ts}{ext}"
        f.save(out)

        if request.args.get("apply") == "1":
            cfg = _load_config()
            cfg["bg_url"] = f"/uploads/{out.name}"
            _save_config(cfg)
        return jsonify({"ok": True, "path": f"/uploads/{out.name}"})

    @app.post("/api/upload/logo")
    def api_upload_logo():
        f = request.files.get("file")
        if not f:
            return jsonify({"ok": False, "error": "no file"}), 400
        ts = time.strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(f.filename or "")[1] or ".png"
        out = UPLOAD_DIR / f"logo_{ts}{ext}"
        f.save(out)

        cfg = _load_config()
        cfg["logo_url"] = f"/uploads/{out.name}"
        _save_config(cfg)
        return jsonify({"ok": True, "path": f"/uploads/{out.name}"})

    # --------------------------- Live Metrics API ----------------------------
    @app.get("/api/live/summary")
    def api_live_summary():
        """
        Format yang dikembalikan:
        {
          guilds, members, channels, threads, online, latency_ms, ts
        }
        File sumber diupdate oleh bot (bebas: data/live.json atau data/presence.json).
        """
        return jsonify(_safe_live_json())

    @app.get("/api/live/presence")
    def api_live_presence():
        cfg = _safe_live_json()
        # tambah uptime sederhana (server side)
        return jsonify({
            "presence": "online" if cfg.get("online", 0) else "idle",
            "latency_ms": cfg.get("latency_ms", 0),
            "ts": cfg.get("ts", int(time.time()))
        })

    # ----------------------------- Health & Uptime ---------------------------
    START_TS = time.time()

    @app.get("/healthz")
    def healthz():
        return "ok", 200

    @app.get("/uptime")
    def uptime():
        return jsonify({"uptime_sec": int(time.time() - START_TS)})

    # ----------------------------- Auth (sederhana) --------------------------
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "admin")

    def _is_authed() -> bool:
        return bool(session.get("authed"))

    def _require_auth():
        if not _is_authed():
            return redirect(url_for("page_login"))

    @app.get("/")
    def root():
        # arahkan ke dashboard jika sudah login, kalau belum ke login
        return redirect(url_for("page_dashboard" if _is_authed() else "page_login"))

    @app.get("/login")
    def page_login():
        return render_template("login.html")

    @app.post("/login")
    def do_login():
        user = request.form.get("username", "")
        pw   = request.form.get("password", "")
        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["authed"] = True
            return redirect(url_for("page_dashboard"))
        return render_template("login.html", error="Username atau password salah.")

    @app.get("/logout")
    def do_logout():
        session.clear()
        return redirect(url_for("page_login"))

    # ----------------------------- Pages -------------------------------------
    @app.get("/dashboard")
    def page_dashboard():
        if not _is_authed():
            return _require_auth()
        return render_template("dashboard.html")

    @app.get("/dashboard/settings")
    def page_settings():
        if not _is_authed():
            return _require_auth()
        return render_template("settings.html")

    return app


# Gunakan app langsung jika file ini dijalankan mandiri
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
