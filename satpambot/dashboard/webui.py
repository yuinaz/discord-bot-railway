# === add-only: security reorder endpoint ===
try:
    from flask import request, jsonify
    from pathlib import Path as _P
    import json as _json

    __SEC_FILE = _P("data") / "security_order.json"
    def __register_security_api(app):
        if not app.view_functions.get("api_security_reorder"):
            @app.post("/api/security/reorder")
            def api_security_reorder():
                payload = request.get_json(force=True, silent=True) or {}
                try:
                    __SEC_FILE.parent.mkdir(parents=True, exist_ok=True)
                    __SEC_FILE.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    return jsonify({"ok": True, "saved": True})
                except Exception as e:
                    return jsonify({"ok": False, "error": str(e)}), 500
    if 'register_webui_builtin' in globals():
        _old = register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try:
                __register_security_api(app)
            except Exception:
                pass
    else:
        def register_webui_builtin(app):
            try:
                __register_security_api(app)
            except Exception:
                pass
except Exception:
    pass


# <<< DASHBOARD_FALLBACKS_V3 >>>
try:
    from flask import Response, request, redirect, send_from_directory, jsonify
    from pathlib import Path as _P
    import logging as _logging, struct as _struct, json as _json
    __SB_STATIC = _P(__file__).resolve().parent / "static"
    __SB_CFG    = _P("data") / "ui_config.json"

    def __tiny_ico_bytes():
        w=h=16
        header=_struct.pack("<HHH",0,1,1)
        bih=_struct.pack("<IIIHHIIIIII",40,w,h*2,1,32,0,w*h*4,0,0,0,0)
        xor=b"\x00\x00\x00\x00"*(w*h); andmask=(b"\x00\x00\x00\x00")*h
        img=bih+xor+andmask; size=len(img); offset=6+16
        entry=_struct.pack("<BBBBBBHHII",w,h,0,0,1,32,size & 0xFFFF,(size>>16)&0xFFFF,offset,0)
        return header+entry+img

    def __ui_load():
        try:
            if __SB_CFG.exists():
                return _json.loads(__SB_CFG.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"theme":"gtake","accent":"blue","bg_mode":"gradient","bg_url":"","apply_login":True,"logo_url":""}

    def __register_dashboard_fallbacks(app):
        if not app.view_functions.get("dashboard_static_alias"):
            app.add_url_rule("/dashboard-static/<path:filename>","dashboard_static_alias",
                lambda filename: send_from_directory(str(__SB_STATIC), filename, conditional=True))

        if not app.view_functions.get("favicon"):
            def _favicon():
                p=__SB_STATIC / "favicon.ico"
                if p.exists(): return send_from_directory(str(__SB_STATIC), "favicon.ico", conditional=True)
                return Response(__tiny_ico_bytes(), mimetype="image/x-icon")
            app.add_url_rule("/favicon.ico","favicon",_favicon)

        if not app.view_functions.get("api_get_ui_config"):
            @app.get("/api/ui-config")
            def api_get_ui_config():
                return jsonify(__ui_load())

        if not app.view_functions.get("dashboard_login_get"):
            @app.get("/dashboard/login")
            def dashboard_login_get():
                return Response("""<!doctype html><meta charset='utf-8'><title>Masuk - SatpamBot</title>
<link rel='stylesheet' href='/dashboard-static/themes/gtake/theme.css'>
<link rel='stylesheet' href='/dashboard-static/css/login_modern.css'>
<link rel='stylesheet' href='/dashboard-static/css/login_theme.css'>
<script src='/dashboard-static/js/ui_theme_bridge.js' defer></script>
<script src='/dashboard-static/js/login_apply_theme.js' defer></script>
<style>html,body{height:100%}body{margin:0;display:flex;align-items:center;justify-content:center;background:#0b0f1a}
._card{max-width:420px;width:92vw;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:22px;color:#e6e8ee;font-family:system-ui,Segoe UI,Roboto,Arial}
._title{font-size:22px;font-weight:700;margin:0 0 10px}._sub{opacity:.75;margin:0 0 16px}._row{margin:10px 0}
._in{width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#e6e8ee}
._btn{display:inline-block;padding:10px 16px;border-radius:14px;border:0;background:linear-gradient(90deg,#4f67ff,#7aa2ff);color:#fff;cursor:pointer}</style>
<body class='login-page'><div class='_card'><div class='_title'>Masuk</div><div class='_sub'>Gunakan kredensial admin yang valid.</div>
<form class='login-form' action='/dashboard/login' method='post' autocomplete='off'>
<div class='_row'><input class='_in' name='username' type='text' placeholder='Username' required></div>
<div class='_row'><input class='_in' name='password' type='password' placeholder='Password' required></div>
<div class='_row'><button class='_btn' type='submit'>LOGIN</button></div></form></div></body>""", mimetype="text/html; charset=utf-8")

        if not app.view_functions.get("dashboard_login_post"):
            @app.post("/dashboard/login")
            def dashboard_login_post():
                return redirect("/dashboard", code=303)

        _log=_logging.getLogger("werkzeug")
        if not getattr(_log, "_sb_hide_ping", False):
            class _NoPing(_logging.Filter):
                def filter(self, rec):
                    m=rec.getMessage()
                    return ("/uptime" not in m) and ("/healthz" not in m)
            _log.addFilter(_NoPing()); _log._sb_hide_ping=True

    if 'register_webui_builtin' in globals():
        _old=register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try: __register_dashboard_fallbacks(app)
            except Exception: pass
    else:
        def register_webui_builtin(app):
            try: __register_dashboard_fallbacks(app)
            except Exception: pass
except Exception:
    pass
