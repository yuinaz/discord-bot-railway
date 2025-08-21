
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from flask import Response, request, redirect, render_template, send_from_directory, jsonify
import json, logging, struct

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_CFG_FILE   = Path("data") / "ui_config.json"

def _has_rule(app, rule: str) -> bool:
    try:
        for r in app.url_map.iter_rules():
            if str(r.rule) == rule:
                return True
    except Exception:
        pass
    return False

def _has_ep(app, name: str) -> bool:
    return name in app.view_functions

def _tiny_ico_bytes() -> bytes:
    w = h = 16
    header = struct.pack("<HHH", 0, 1, 1)
    bih    = struct.pack("<IIIHHIIIIII", 40, w, h*2, 1, 32, 0, w*h*4, 0, 0, 0, 0)
    xor    = b"\\x00\\x00\\x00\\x00" * (w*h)
    andmsk = (b"\\x00\\x00\\x00\\x00") * h
    img    = bih + xor + andmsk
    size   = len(img); offset = 6 + 16
    entry  = struct.pack("<BBBBBBHHII", w, h, 0, 0, 1, 32, size & 0xFFFF, (size>>16)&0xFFFF, offset, 0)
    return header + entry + img

def _ui_load() -> dict:
    try:
        if _CFG_FILE.exists():
            return json.loads(_CFG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"theme":"gtake","accent":"blue","bg_mode":"gradient","bg_url":"","apply_login":True,"logo_url":""}

def register_webui_builtin(app):
    if not _has_ep(app, "dashboard_static"):
        app.add_url_rule("/dashboard-static/<path:filename>", "dashboard_static",
            lambda filename: send_from_directory(str(_STATIC_DIR), filename, conditional=True))

    if not _has_ep(app, "favicon"):
        def _favicon():
            p = _STATIC_DIR / "favicon.ico"
            if p.exists(): return send_from_directory(str(_STATIC_DIR), "favicon.ico", conditional=True)
            return Response(_tiny_ico_bytes(), mimetype="image/x-icon")
        app.add_url_rule("/favicon.ico", "favicon", _favicon)

    if not _has_ep(app, "api_get_ui_config"):
        @app.get("/api/ui-config")
        def api_get_ui_config():
            return jsonify(_ui_load())

    if not _has_ep(app, "dashboard_login_get"):
        @app.get("/dashboard/login")
        def dashboard_login_get():
            try:
                return render_template("login.html")
            except Exception:
                return Response("<!doctype html><title>Login</title><p>Template login.html tidak ditemukan.</p>", mimetype="text/html; charset=utf-8")

    if not _has_ep(app, "dashboard_login_post"):
        @app.post("/dashboard/login")
        def dashboard_login_post():
            return redirect("/dashboard", code=303)

    if not _has_ep(app, "dashboard_index") and not _has_rule(app, "/dashboard"):
        @app.get("/dashboard")
        def dashboard_index():
            try:
                return render_template("dashboard.html")
            except Exception:
                html = ("<!doctype html><meta charset='utf-8'>"
                        "<link rel='stylesheet' href='/dashboard-static/css/neo_aurora_plus.css'>"
                        "<div class='container'><div class='card'><h1>Dashboard</h1>"
                        "<p>Template dashboard.html belum ditemukan.</p></div></div>")
                return Response(html, mimetype="text/html; charset=utf-8")

    if not _has_ep(app, "dashboard_slash"):
        @app.get("/dashboard/")
        def dashboard_slash():
            return redirect("/dashboard", code=302)

    if not _has_rule(app, "/") and not _has_ep(app, "root_redirect_to_dashboard"):
        @app.get("/")
        def root_redirect_to_dashboard():
            return redirect("/dashboard", code=302)

    _log = logging.getLogger("werkzeug")
    if not getattr(_log, "_sb_hide_ping_ui", False):
        class _NoPing(logging.Filter):
            def filter(self, rec):
                m = rec.getMessage()
                return ("/uptime" not in m) and ("/healthz" not in m)
        _log.addFilter(_NoPing()); _log._sb_hide_ping_ui = True

__all__ = ["register_webui_builtin"]


# <<< SB_JINJA_BRIDGE >>>
try:
    from jinja2 import ChoiceLoader, FileSystemLoader
    from pathlib import Path as _P
    _SB_TEMPL_DIR = _P(__file__).resolve().parent / "templates"

    def _sb_attach_jinja_loader(app):
        try:
            loader_now = getattr(app, "jinja_loader", None)
            add_loader = FileSystemLoader(str(_SB_TEMPL_DIR))
            if loader_now and isinstance(loader_now, ChoiceLoader):
                paths=[]
                for L in loader_now.loaders:
                    p=getattr(L,"searchpath",None)
                    if isinstance(p,(list,tuple)):
                        paths += list(map(str,p))
                if str(_SB_TEMPL_DIR) not in paths:
                    app.jinja_loader = ChoiceLoader(list(loader_now.loaders)+[add_loader])
            else:
                app.jinja_loader = ChoiceLoader([loader_now, add_loader] if loader_now else [add_loader])
        except Exception:
            pass

    if 'register_webui_builtin' in globals():
        _old = register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            _sb_attach_jinja_loader(app)
    else:
        def register_webui_builtin(app):
            _sb_attach_jinja_loader(app)
except Exception:
    pass
