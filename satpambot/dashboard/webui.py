# satpambot/dashboard/webui.py
import json
import re
from pathlib import Path

from flask import (
    Response, jsonify, redirect, render_template,
    request, send_from_directory
)
from jinja2 import ChoiceLoader, FileSystemLoader

# === Paths ===
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_TEMPL_DIR  = Path(__file__).resolve().parent / "templates"
_THEMES_DIR = Path(__file__).resolve().parent / "themes"
_CFG_FILE   = Path("data") / "ui_config.json"


# === Helpers ===
def _has_ep(app, name: str) -> bool:
    return name in app.view_functions

def _has_rule(app, rule: str) -> bool:
    try:
        app.url_map.bind("").match(rule, "GET")
        return True
    except Exception:
        return False

def _ui_load() -> dict:
    try:
        if _CFG_FILE.exists():
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _ui_save(cfg: dict):
    try:
        _CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CFG_FILE.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

def _safe_theme_name(name: str) -> str:
    name = (name or "").strip().lower()
    if not re.match(r"^[a-z0-9_\-]+$", name):
        return "classic"
    return name or "classic"

def _get_theme() -> str:
    return _safe_theme_name(_ui_load().get("theme", "classic"))

def _theme_list():
    if not _THEMES_DIR.exists():
        return ["classic"]
    items = [p.name for p in _THEMES_DIR.iterdir() if p.is_dir()]
    return sorted(items) or ["classic"]

def _render_themed(app, template_name: str, **ctx):
    """Prefer override: themes/<active>/templates/<template_name>."""
    theme = _get_theme()
    ctx.setdefault("theme", theme)
    themed_file = _THEMES_DIR / theme / "templates" / template_name
    if themed_file.exists():
        return Response(themed_file.read_text(encoding="utf-8"),
                        mimetype="text/html; charset=utf-8")
    return render_template(template_name, **ctx)


# === Public API ===
def register_webui_builtin(app):
    """Register routes & assets for the dashboard without touching other configs."""

    # Attach default templates path into Jinja loader (non-destructive)
    try:
        loader_now = getattr(app, "jinja_loader", None)
        add_loader = FileSystemLoader(str(_TEMPL_DIR))
        if loader_now and isinstance(loader_now, ChoiceLoader):
            paths = []
            for L in loader_now.loaders:
                p = getattr(L, "searchpath", None)
                if isinstance(p, (list, tuple)):
                    paths += list(map(str, p))
            if str(_TEMPL_DIR) not in paths:
                app.jinja_loader = ChoiceLoader(list(loader_now.loaders) + [add_loader])
        else:
            app.jinja_loader = ChoiceLoader([loader_now, add_loader] if loader_now else [add_loader])
    except Exception:
        pass

    # ---------- Static bridges ----------
    if not _has_ep(app, "dashboard_static"):
        @app.get("/dashboard-static/<path:filename>")
        def dashboard_static(filename):
            return send_from_directory(str(_STATIC_DIR), filename, conditional=True)

    if not _has_ep(app, "dashboard_theme_static"):
        @app.get("/dashboard-theme/<theme>/<path:filename>")
        def dashboard_theme_static(theme, filename):
            theme = _safe_theme_name(theme)
            base = _THEMES_DIR / theme / "static"
            return send_from_directory(str(base), filename, conditional=True)

    # ---------- Aliases ----------
    if not _has_ep(app, "alias_root"):
        @app.get("/")
        def alias_root():
            return redirect("/dashboard", code=302)

    if not _has_ep(app, "alias_login"):
        @app.get("/login")
        def alias_login():
            return redirect("/dashboard/login", code=302)

    # ---------- UI Config API ----------
    if not _has_ep(app, "api_get_ui_config"):
        @app.get("/api/ui-config")
        def api_get_ui_config():
            return jsonify(_ui_load())

    if not _has_ep(app, "api_set_ui_config"):
        @app.post("/api/ui-config")
        def api_set_ui_config():
            try:
                data = request.get_json(force=True) or {}
            except Exception:
                return jsonify({"ok": False, "error": "bad-json"}), 400
            allow = {"theme", "accent", "bg_mode", "bg_url", "apply_login", "logo_url"}
            cfg = _ui_load()
            for k, v in data.items():
                if k in allow:
                    cfg[k] = v
            _ui_save(cfg)
            return jsonify({"ok": True, "saved": cfg})

    if not _has_ep(app, "api_ui_themes"):
        @app.get("/api/ui-themes")
        def api_ui_themes():
            return jsonify({"themes": _theme_list(), "active": _get_theme()})

    # ---------- Pages (themed) ----------
    if not _has_ep(app, "dashboard_login_get"):
        @app.get("/dashboard/login")
        def dashboard_login_get():
            try:
                return _render_themed(app, "login.html")
            except Exception:
                p = _TEMPL_DIR / "login.html"
                if p.exists():
                    return Response(p.read_text(encoding="utf-8"),
                                    mimetype="text/html; charset=utf-8")
                return Response("Template login.html tidak ditemukan.",
                                mimetype="text/plain; charset=utf-8")

    if not _has_ep(app, "dashboard_login_post"):
        @app.post("/dashboard/login")
        def dashboard_login_post():
            # autentikasi sederhana sudah ditangani di app lain;
            # di sini cukup redirect agar kompatibel dengan setup kamu.
            return redirect("/dashboard", code=303)

    if not _has_ep(app, "dashboard_index") and not _has_rule(app, "/dashboard"):
        @app.get("/dashboard")
        def dashboard_index():
            try:
                return _render_themed(app, "dashboard.html")
            except Exception:
                p = _TEMPL_DIR / "dashboard.html"
                if p.exists():
                    return Response(p.read_text(encoding="utf-8"),
                                    mimetype="text/html; charset=utf-8")
                html = ("<!doctype html><meta charset='utf-8'>"
                        "<link rel='stylesheet' href='/dashboard-static/css/neo_aurora_plus.css'>"
                        "<div class='container'><div class='card'><h1>Dashboard</h1>"
                        "<p>Template dashboard.html belum ditemukan.</p></div></div>")
                return Response(html, mimetype="text/html; charset=utf-8")

    if not _has_ep(app, "dashboard_settings"):
        @app.get("/dashboard/settings")
        def dashboard_settings():
            try:
                return _render_themed(app, "settings.html")
            except Exception:
                p = _TEMPL_DIR / "settings.html"
                if p.exists():
                    return Response(p.read_text(encoding="utf-8"),
                                    mimetype="text/html; charset=utf-8")
                return Response("<h1>Settings</h1><p>Template settings.html belum ada.</p>",
                                mimetype="text/html; charset=utf-8")

    if not _has_ep(app, "dashboard_security"):
        @app.get("/dashboard/security")
        def dashboard_security():
            try:
                return _render_themed(app, "security.html")
            except Exception:
                p = _TEMPL_DIR / "security.html"
                if p.exists():
                    return Response(p.read_text(encoding="utf-8"),
                                    mimetype="text/html; charset=utf-8")
                return Response("<h1>Security</h1><p>Template security.html belum ada.</p>",
                                mimetype="text/html; charset=utf-8")

    # ---------- Upload endpoints ----------
    if not _has_ep(app, "dashboard_upload"):
        @app.post("/dashboard/upload")
        def dashboard_upload():
            f = request.files.get("file")
            if not f or not f.filename:
                return jsonify({"ok": False, "error": "no-file"}), 400
            updir = Path("data") / "uploads" / "dashboard"
            updir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f.filename)
            dst = updir / safe
            f.save(dst)
            return jsonify({"ok": True, "saved": str(dst)})

    if not _has_ep(app, "dashboard_security_upload"):
        @app.post("/dashboard/security/upload")
        def dashboard_security_upload():
            f = request.files.get("file")
            if not f or not f.filename:
                return jsonify({"ok": False, "error": "no-file"}), 400
            updir = Path("data") / "uploads" / "security"
            updir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", f.filename)
            dst = updir / safe
            f.save(dst)
            return jsonify({"ok": True, "saved": str(dst)})

    # ---------- Logout pages (additive, tidak mengganggu config lain) ----------
    if not _has_ep(app, "logout_page"):
        @app.get("/logout")
        def logout_page():
            # Coba render override tema terlebih dahulu, lalu fallback ke templates/logout.html
            try:
                return _render_themed(app, "logout.html")
            except Exception:
                # Fallback sangat sederhana, tetap mengarahkan ke login
                return Response(
                    "<h1>Anda telah logout.</h1>"
                    "<script>setTimeout(()=>location.href='/dashboard/login',1000)</script>",
                    mimetype="text/html; charset=utf-8"
                )

    if not _has_ep(app, "dashboard_logout"):
        @app.get("/dashboard/logout")
        def dashboard_logout():
            # Alias supaya tautan ke /dashboard/logout tetap valid
            return redirect("/logout", code=302)


__all__ = ["register_webui_builtin"]
