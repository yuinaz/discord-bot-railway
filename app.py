
# app.py — loader + SAFE alias routes (/login, /settings), Render free-plan friendly
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
    for mod_name in candidates:
        try:
            mod = import_module(mod_name)
        except Exception as e:
            log.debug("skip %s: %s", mod_name, e)
            continue
        # direct instance
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

    # fallback tiny app to avoid None
    from flask import Flask
    app = Flask("satpambot_fallback")
    @app.get("/")
    def _root(): return "SatpamBot dashboard fallback", 200
    @app.get("/healthz")
    def _h(): return "ok", 200
    @app.get("/uptime")
    def _u(): return {"uptime_sec": int(time.time() - app.config.get("START_TIME", time.time()))}, 200
    log.warning("[app] fallback Flask app created")
    return app

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
        silence_healthz_logs(); ensure_healthz_route(app); ensure_uptime_route(app)
    except Exception as e:
        log.debug("healthz wiring skipped: %s", e)

def _ensure_aliases(app):
    """Add /login and /settings aliases if missing. Use unique endpoints to avoid AssertionError."""
    from flask import redirect
    existing = {r.rule for r in app.url_map.iter_rules()}

    def _add_alias(alias: str, target: str):
        endpoint = f"alias_{alias.strip('/').replace('/', '_') or 'root'}"
        if alias in existing:
            return
        if endpoint in getattr(app, "view_functions", {}):
            endpoint = f"{endpoint}_{int(time.time()*1000)%100000}"
        def _view(target=target):
            return redirect(target, code=302)
        app.add_url_rule(alias, endpoint=endpoint, view_func=_view, methods=["GET"])
        log.info("[alias] %s -> %s (endpoint=%s)", alias, target, endpoint)

    alias_map = {
        "/login": ["/dashboard/login", "/auth/login", "/signin", "/"],
        "/settings": ["/dashboard/settings", "/settings/", "/"],
    }
    for alias, cands in alias_map.items():
        if alias in existing:
            continue
        target = None
        for c in cands:
            if c in existing:
                target = c; break
        if target is None:
            target = "/"
        _add_alias(alias, target)

def create_app():
    app = _resolve_app()
    _wire_healthz(app)
    _ensure_aliases(app)
    return app

# Export global app (backward compatible)
app = create_app()
