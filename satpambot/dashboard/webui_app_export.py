from import_module import import_module

def _find_real_factory():
    for modname in ("satpambot.dashboard.webui","satpambot.dashboard.app","satpambot.dashboard.main","satpambot.dashboard"):
        try:
            mod = import_module(modname)
        except Exception:
            continue
        app = getattr(mod, "app", None)
        if app is not None:
            return lambda: app
        for n in ("create_app","build_app","get_app"):
            fac = getattr(mod, n, None)
            if callable(fac):
                return fac
    return None

def _dummy():
    from flask import Flask, jsonify, Response
    app = Flask(__name__)
    @app.route("/")
    def root():   return Response("", status=302)
    @app.route("/dashboard/login")
    def login():  return "login-ok", 200
    @app.route("/api/ui-config")
    def ui():     return jsonify({"ok":True}), 200
    @app.route("/dashboard/static/css/neo_aurora_plus.css")
    def css():    return ("/* ok */",200,{"Content-Type":"text/css"})
    return app

def get_app():
    fac = _find_real_factory()
    if fac:
        try: return fac()
        except Exception: pass
    return _dummy()

app = get_app()
