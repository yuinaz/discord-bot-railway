
# app.py — minimal loader (Render-safe) that doesn't touch other modules
from __future__ import annotations
import logging, time
from importlib import import_module

log = logging.getLogger("app_loader")
logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(message)s")

def _resolve_app():
    """Try multiple sources to get a Flask app instance or factory."""
    candidates = [
        "satpambot.dashboard.webui",
        "satpambot.dashboard.app_dashboard",
        "app_dashboard",
    ]
    # patterns: module.app or module.create_app()
    for mod_name in candidates:
        try:
            mod = import_module(mod_name)
        except Exception as e:
            log.debug("skip %s: %s", mod_name, e)
            continue
        # direct app
        app = getattr(mod, "app", None)
        if app is not None:
            log.info("[app] using %s:app", mod_name)
            return app
        # factory
        create_app = getattr(mod, "create_app", None)
        if callable(create_app):
            try:
                app = create_app()
                log.info("[app] using %s:create_app()", mod_name)
                return app
            except Exception as e:
                log.warning("create_app() failed in %s: %s", mod_name, e)

    # last resort: tiny Flask app
    try:
        from flask import Flask
        app = Flask("satpambot_fallback")
        @app.get("/healthz")
        def _health(): return "ok", 200
        @app.get("/uptime")
        def _up(): return {"uptime_sec": int(time.time() - app.config.get("START_TIME", time.time()))}, 200
        log.warning("[app] fallback Flask app created")
        return app
    except Exception as e:
        raise RuntimeError(f"Cannot construct Flask app: {e}")

def _wire_healthz(app):
    """Ensure quiet healthz & uptime routes if utility exists (no-op otherwise)."""
    try:
        from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route, ensure_uptime_route
    except Exception:
        def silence_healthz_logs(*a, **k): pass
        def ensure_healthz_route(app): 
            if not any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
                @app.get("/healthz")
                def _h(): return "ok", 200
        def ensure_uptime_route(app):
            if not any(r.rule == "/uptime" for r in app.url_map.iter_rules()):
                start = time.time()
                @app.get("/uptime")
                def _u(): return {"uptime_sec": int(time.time()-start)}, 200
    try:
        silence_healthz_logs()
        ensure_healthz_route(app)
        ensure_uptime_route(app)
    except Exception as e:
        log.debug("healthz wiring skipped: %s", e)

def create_app():
    app = _resolve_app()
    _wire_healthz(app)
    return app

# Export a global app to keep previous behavior
app = create_app()
