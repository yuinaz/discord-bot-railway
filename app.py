# app.py — WSGI entry for Render (fail-fast, no silent fallback)
from __future__ import annotations
import os, logging
from importlib import import_module
from flask import Flask, redirect

log = logging.getLogger("satpambot.app")
logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"))

def _load_real_app() -> Flask:
    """
    Try to load the real dashboard app from satpambot.dashboard.app_dashboard or app_dashboard.
    Must succeed; otherwise raise to make Render logs obvious (fail fast).
    """
    errors = []
    for name in ("satpambot.dashboard.app_dashboard", "app_dashboard"):
        try:
            mod = import_module(name)
            app = getattr(mod, "app", None)
            if app is None and hasattr(mod, "create_app"):
                app = mod.create_app()
            if isinstance(app, Flask):
                log.info("[app] loaded dashboard from %s", name)
                return app
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("Failed to load dashboard app. Tried: " + "; ".join(errors))

def create_app() -> Flask:
    app = _load_real_app()

    # Optional: quiet healthz logs + ensure /healthz and /uptime routes
    try:
        from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route, ensure_uptime_route
        silence_healthz_logs()
        ensure_healthz_route(app)
        ensure_uptime_route(app)
    except Exception as e:
        log.debug("[app] healthz/uptime helpers not applied: %s", e)

    # Optional: register builtin web UI (idempotent; serves /dashboard + /api/*)
    try:
        from satpambot.dashboard.webui import register_webui_builtin
        register_webui_builtin(app)
    except Exception as e:
        log.debug("[app] builtin webui not registered: %s", e)

    # Friendly aliases without endpoint clashes.
    def _alias(rule: str, target: str):
        ep = f"_alias_{rule.strip('/').replace('/','_') or 'root'}"
        if ep not in app.view_functions:
            app.add_url_rule(rule, ep, (lambda t=target: redirect(t, code=302)))

    try:
        _alias("/", "/login")                 # root -> login
        _alias("/dashboard", "/")             # /dashboard -> /
        _alias("/settings", "/dashboard/settings")
        _alias("/security", "/dashboard/security")
    except Exception as e:
        log.debug("[app] alias attach failed: %s", e)

    return app

# WSGI object expected by Render when start command is `python main.py`
app = None  # will be created by main.py via create_app()

if __name__ == "__main__":
    # Allow `python app.py` locally
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","10000")), debug=False)
