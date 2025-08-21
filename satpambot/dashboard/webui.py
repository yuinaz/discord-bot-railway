from __future__ import annotations
from flask import Blueprint, render_template

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/dashboard",
)

@dashboard_bp.get("/")
def page_dashboard(): return render_template("dashboard.html")

@dashboard_bp.get("/login")
def page_login(): return render_template("login.html")

@dashboard_bp.get("/settings")
def page_settings(): return render_template("settings.html")

@dashboard_bp.get("/security")
def page_security(): return render_template("security.html")

def register_webui_builtin(app):
    if "dashboard" not in app.blueprints:
        app.register_blueprint(dashboard_bp)



# === add-only: /uptime endpoint + access log filter (no env needed) ===
try:
    import logging as __logging
    from flask import Response as __Response

    def __register_uptime_inline(app):
        # 1) Route: /uptime → "OK" (GET/HEAD)
        if not app.view_functions.get("uptime_ping"):
            @app.get("/uptime")
            def uptime_ping():
                return __Response("OK", mimetype="text/plain")

        # 2) Suppress /uptime & /healthz in Werkzeug access log (once)
        _log = __logging.getLogger("werkzeug")
        if not getattr(_log, "_uptime_filter_added", False):
            class _NoPing(__logging.Filter):
                def filter(self, record):
                    msg = record.getMessage()
                    return ("/uptime" not in msg) and ("/healthz" not in msg)
            _log.addFilter(_NoPing())
            _log._uptime_filter_added = True

    # Hook into existing register_webui_builtin(app)
    if 'register_webui_builtin' in globals():
        _old__register = register_webui_builtin
        def register_webui_builtin(app):
            _old__register(app)
            try:
                __register_uptime_inline(app)
            except Exception:
                pass
except Exception:
    # never crash app if anything above fails
    pass

# === add-only: robust extras for static+api+uptime+favicon+login (no env) ===
try:
    from flask import send_from_directory, jsonify, request, redirect, Response
    from pathlib import Path as _P
    import json as _json, logging as _logging, struct as _struct

    __SB_STATIC = _P(__file__).resolve().parent / "static"
    __SB_DATA   = _P("data"); __SB_UP = __SB_DATA / "uploads"; __SB_CFG = __SB_DATA / "ui_config.json"
    for __p in (__SB_DATA, __SB_UP):
        try: __p.mkdir(parents=True, exist_ok=True)
        except Exception: pass

    def __sb_ui_load():
        try:
            if __SB_CFG.exists():
                return _json.loads(__SB_CFG.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"theme":"gtake","accent":"blue","bg_mode":"gradient","bg_url":"","apply_login":True,"logo_url":""}

    def __sb_ui_save(cfg:dict):
        try:
            __SB_CFG.write_text(_json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def __tiny_ico_bytes():
        # build 16x16 transparent ICO (32-bit BGRA) programmatically
        w=h=16
        header = _struct.pack("<HHH", 0, 1, 1)
        bih = _struct.pack("<IIIHHIIIIII", 40, w, h*2, 1, 32, 0, w*h*4, 0, 0, 0, 0)
        xor = b"\x00\x00\x00\x00" * (w*h)
        andmask = (b"\x00\x00\x00\x00") * h
        img = bih + xor + andmask
        size = len(img); offset = 6+16
        entry = _struct.pack("<BBBBBBHHII", w, h, 0, 0, 1, 32, size & 0xFFFF, (size>>16)&0xFFFF, offset, 0)
        return header + entry + img

    def __sb_register_extras(app):
        # 1) static alias
        if not app.view_functions.get("dashboard_static_alias"):
            app.add_url_rule("/dashboard-static/<path:filename>", "dashboard_static_alias",
                lambda filename: send_from_directory(str(__SB_STATIC), filename, conditional=True))

        # 2) uploads passthrough
        if not app.view_functions.get("uploads"):
            app.add_url_rule("/uploads/<path:filename>", "uploads",
                lambda filename: send_from_directory(str(__SB_UP), filename, conditional=True))

        # 3) favicon (file jika ada, fallback ICO in-memory)
        if not app.view_functions.get("favicon"):
            def _favicon():
                p = __SB_STATIC / "favicon.ico"
                if p.exists():
                    return send_from_directory(str(__SB_STATIC), "favicon.ico", conditional=True)
                return Response(__tiny_ico_bytes(), mimetype="image/x-icon")
            app.add_url_rule("/favicon.ico", "favicon", _favicon)

        # 4) ui-config
        if not app.view_functions.get("api_get_ui_config"):
            @app.get("/api/ui-config")
            def api_get_ui_config():
                return jsonify(__sb_ui_load())
        if not app.view_functions.get("api_post_ui_config"):
            @app.post("/api/ui-config")
            def api_post_ui_config():
                payload = request.get_json(force=True, silent=True) or {}
                cfg = __sb_ui_load()
                for k in ("theme","accent","bg_mode","bg_url","logo_url","apply_login"):
                    if k in payload: cfg[k] = payload[k]
                __sb_ui_save(cfg)
                return jsonify({"ok": True, "config": cfg})

        # 5) login POST -> redirect (hindari 405 pada tema login)
        if not app.view_functions.get("dashboard_login_post"):
            @app.post("/dashboard/login")
            def dashboard_login_post():
                return redirect("/dashboard", code=303)

        # 6) uptime + filter log untuk /uptime & /healthz
        if not app.view_functions.get("uptime_ping"):
            @app.get("/uptime")
            def uptime_ping():
                return Response("OK", mimetype="text/plain")
            app.add_url_rule("/uptime", "uptime_head", lambda: Response("OK", mimetype="text/plain"), methods=["HEAD"])
        _log = _logging.getLogger("werkzeug")
        if not getattr(_log, "_sb_uptime_filter", False):
            class _NoPing(_logging.Filter):
                def filter(self, record):
                    m = record.getMessage()
                    return ("/uptime" not in m) and ("/healthz" not in m)
            _log.addFilter(_NoPing())
            _log._sb_uptime_filter = True

    # Hook ke register_webui_builtin yang sudah ada
    if 'register_webui_builtin' in globals():
        _old = register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try:
                __sb_register_extras(app)
            except Exception:
                pass
    else:
        def register_webui_builtin(app):
            try:
                __sb_register_extras(app)
            except Exception:
                pass
except Exception:
    # jangan pernah bikin app crash
    pass
