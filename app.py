# Robust WSGI entrypoint for Render: expose `app`
import logging, os
from importlib import import_module

# Import helpers (no-op fallbacks if missing)
try:
    from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route
except Exception:
    def silence_healthz_logs(*args, **kwargs): pass
    def ensure_healthz_route(app): pass

try:
    from satpambot.dashboard.webui import register_webui as _register_webui_bp
except Exception:
    def _register_webui_bp(app): pass

# Try to import the real dashboard app defined by project
def _load_app():
    # Preferred location
    candidates = [
        "satpambot.dashboard.app_dashboard",
        "app_dashboard",  # fallback if app_dashboard.py is at project root
    ]
    for modname in candidates:
        try:
            mod = import_module(modname)
        except Exception:
            continue
        # common names: app / create_app()
        app = getattr(mod, "app", None)
        if app is not None:
            return app

        create_app = getattr(mod, "create_app", None)
        if create_app is not None:
            try:
                app = create_app()
                if app is not None:
                    return app
            except Exception:
                pass
    # Last resort minimal Flask app (should not be used in normal deploys)
    from flask import Flask
    _app = Flask(__name__)
    @_app.get("/")
    def _root():
        return "OK", 200
    return _app

app = _load_app()

# Quiet noisy access logs AFTER we successfully have an app
try:
    silence_healthz_logs()
except Exception:
    pass

# Ensure /healthz exists (idempotent)
try:
    ensure_healthz_route(app)
except Exception:
    pass

# Only register our lightweight dashboard blueprint if "/" is not already handled.
def _has_root_route(_app):
    try:
        for r in _app.url_map.iter_rules():
            if r.rule == "/":
                return True
    except Exception:
        pass
    return False

try:
    if not _has_root_route(app):
        _register_webui_bp(app)
except Exception:
    pass
