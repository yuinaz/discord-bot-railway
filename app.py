# WSGI entry for Render + optional direct runner.
import os
from importlib import import_module

def _noop(*a, **k): ...
try:
    from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route
except Exception:
    silence_healthz_logs = _noop
    def ensure_healthz_route(app): pass

def _load_real_app():
    for name in ("satpambot.dashboard.app_dashboard", "app_dashboard"):
        try:
            mod = import_module(name)
            app = getattr(mod, "app", None) or (getattr(mod, "create_app", None) and mod.create_app())
            if app: return app
        except Exception:
            continue
    from flask import Flask
    app = Flask(__name__)
    @app.get("/")
    def _root(): return "OK", 200
    return app

app = _load_real_app()

try: silence_healthz_logs()
except Exception: pass
try: ensure_healthz_route(app)
except Exception: pass

# Register builtin dashboard blueprint (idempotent, serves /dashboard and /api/* only)
try:
    from satpambot.dashboard.webui import register_webui_builtin
    register_webui_builtin(app)
except Exception:
    pass

if __name__ == "__main__":
    # Allow running: python app.py (Render will set $PORT)
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
