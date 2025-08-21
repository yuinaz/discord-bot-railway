from __future__ import annotations
import os
import logging
from pathlib import Path
from flask import Flask, redirect

log = logging.getLogger("satpambot.app")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "satpambot" / "dashboard"
TPL  = DASH / "templates"
STA  = DASH / "static"

def _add_alias(app: Flask, alias: str, target: str):
    ep = f"_alias_{alias.strip('/').replace('/','_') or 'root'}"
    if ep in app.view_functions:
        return
    app.add_url_rule(alias, ep, (lambda t=target: redirect(t, code=302)))

def create_app() -> Flask:
    app = Flask(
        "satpambot_dashboard",
        template_folder=str(TPL),
        static_folder=str(STA),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-only-local")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
    upload_base = Path(os.getenv("UPLOAD_DIR", "/var/data/uploads"))
    if not upload_base.exists():
        upload_base = ROOT / "data" / "uploads"
    upload_base.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_base)

    # Register dashboard blueprint (fail fast if missing)
    from satpambot.dashboard.webui import bp as dashboard_bp  # must exist
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    # Health & uptime (if helpers exist)
    try:
        from satpambot.dashboard.healthz_quiet import ensure_healthz_route, ensure_uptime_route
        ensure_healthz_route(app)
        ensure_uptime_route(app)
    except Exception:
        # Minimal health route fallback
        @app.get("/healthz")
        def _healthz_ok():
            return "OK", 200

    # Nice aliases
    _add_alias(app, "/",          "/dashboard/login")
    _add_alias(app, "/login",     "/dashboard/login")
    _add_alias(app, "/settings",  "/dashboard/settings")
    _add_alias(app, "/security",  "/dashboard/security")

    tz = os.getenv("TZ", "Asia/Jakarta")
    try:
        os.environ["TZ"] = tz
    except Exception:
        pass
    log.info("[app] Flask created; templates=%s static=%s uploads=%s tz=%s",
             app.template_folder, app.static_folder, app.config["UPLOAD_FOLDER"], tz)
    return app
