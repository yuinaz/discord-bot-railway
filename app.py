# WSGI entry for Render + optional direct runner.
import os, logging, time
from importlib import import_module
from flask import Flask

def _load_real_app():
    for name in ("satpambot.dashboard.app_dashboard", "app_dashboard"):
        try:
            mod = import_module(name)
            app = getattr(mod, "app", None) or (getattr(mod, "create_app", None) and mod.create_app())
            if app: return app
        except Exception:
            continue
    return None

app = _load_real_app() or Flask(__name__)

# Basic secure defaults
app.config.setdefault("SECRET_KEY", os.getenv("SECRET_KEY","changeme-secret-key"))
app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
if os.getenv("FORCE_SECURE_COOKIES","1") in ("1","true","yes","on"):
    app.config.setdefault("SESSION_COOKIE_SECURE", True)

# Health & uptime routes + silence logs
def _noop(*a, **k): ...
try:
    from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route, ensure_uptime_route
except Exception:
    silence_healthz_logs = _noop
    ensure_healthz_route = lambda app: None  # type: ignore
    ensure_uptime_route = lambda app: None  # type: ignore

try:
    silence_healthz_logs()
except Exception:
    pass
try:
    ensure_healthz_route(app)
    ensure_uptime_route(app)
except Exception:
    pass

# Optional: register builtin web UI (if available)
try:
    from satpambot.dashboard.webui import register_webui_builtin
    register_webui_builtin(app)
except Exception:
    pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
