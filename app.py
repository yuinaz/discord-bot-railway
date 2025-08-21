# app.py — ENTRY FLASK (dashboard)
from __future__ import annotations
import logging, os
from flask import Flask, redirect, Response

log = logging.getLogger("entry.app")

def _try_register_webui(app: Flask) -> None:
    tried = []
    for mod in ("satpambot.dashboard.webui","dashboard.webui","webui"):
        try:
            m = __import__(mod, fromlist=["register_webui_builtin"])
            m.register_webui_builtin(app)
            log.info("Dashboard loaded via %s", mod)
            return
        except Exception as e:
            tried.append(f"{mod}: {e.__class__.__name__}")
            log.debug("Dashboard import failed: %s", mod, exc_info=True)
    log.error("No dashboard blueprint registered. Tried: %s", ", ".join(tried))
    log.error("Dashboard failed to load - check import errors above.")

def _ensure_healthz(app: Flask) -> None:
    if any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
        return
    @app.get("/healthz")
    def _healthz():
        return Response("OK", mimetype="text/plain")
    class _HealthzFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return "/healthz" not in str(getattr(record, "msg", ""))
    logging.getLogger("werkzeug").addFilter(_HealthzFilter())

def _register_aliases(app: Flask) -> None:
    def _alias(rule: str, target: str):
        if any(r.rule == rule for r in app.url_map.iter_rules()):
            return
        endpoint = f"_alias_{rule.replace('/', '_') or 'root'}"
        @app.get(rule, endpoint=endpoint)
        def _go():  # type: ignore
            return redirect(target, code=302)
        log.info("[alias] %s -> %s", rule, target)
    _alias("/", "/dashboard")
    _alias("/login", "/dashboard/login")
    _alias("/settings", "/dashboard/settings")
    _alias("/security", "/dashboard/security")

def _attach_extra_api(app: Flask) -> None:
    for mod, attr in (
        ("satpambot.dashboard.live_routes", "api_bp"),
        ("satpambot.dashboard.presence_api", "presence_bp"),
    ):
        try:
            m = __import__(mod, fromlist=[attr])
            bp = getattr(m, attr)
            if bp.name not in app.blueprints:
                app.register_blueprint(bp)
                log.info("Registered blueprint: %s", bp.name)
        except Exception:
            log.debug("Skip attaching %s", mod, exc_info=True)

def _ensure_uptime(app: Flask) -> None:
    if any(r.rule == "/uptime" for r in app.url_map.iter_rules()):
        return
    @app.get("/uptime")
    def _uptime():
        return Response("OK", mimetype="text/plain")

def create_app() -> Flask:
    app = Flask("satpambot_dashboard")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "satpambot-secret")
    _ensure_healthz(app)
    _try_register_webui(app)
    _attach_extra_api(app)
    _register_aliases(app)
    _ensure_uptime(app)
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)


# --- Added: silence health endpoints in logs (safe) ---

def _install_health_log_filter(app):
    try:
        import logging
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                for token in ('/healthz','/health','/ping'):
                    if token in msg:
                        return False
                return True
        logging.getLogger('werkzeug').addFilter(_HealthzFilter())
        logging.getLogger('gunicorn.access').addFilter(_HealthzFilter())
    except Exception:
        pass

try:
    _install_health_log_filter(None)
except Exception:
    pass
