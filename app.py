from __future__ import annotations
import os, time, logging
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, redirect, jsonify

log = logging.getLogger("satpambot.app")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

ROOT = Path(__file__).resolve().parent
DASH = ROOT / "satpambot" / "dashboard"
TPL  = DASH / "templates"
STA  = DASH / "static"

def _alias(app: Flask, src: str, dst: str):
    """Register redirect alias with a unique endpoint to avoid collisions."""
    ep = f"alias__{src.strip('/').replace('/','_') or 'root'}"
    if ep in app.view_functions:
        return
    app.add_url_rule(src, endpoint=ep, view_func=(lambda target=dst: redirect(target, code=302)))

def _wire_health(app: Flask):
    """
    Prefer the project's quiet health routes if available, otherwise provide
    minimal /healthz and JSON /uptime for UptimeRobot.
    """
    try:
        from satpambot.dashboard.healthz_quiet import ensure_healthz_route, ensure_uptime_route
        ensure_healthz_route(app)
        ensure_uptime_route(app)
        return
    except Exception:
        pass

    @app.get("/healthz")
    def _healthz_ok():
        return "OK", 200

    @app.get("/uptime")
    def _uptime():
        start = app.config.get("START_TIME") or time.time()
        now = time.time()
        started_at = datetime.fromtimestamp(start, tz=timezone.utc).isoformat()
        return jsonify(
            status="ok",
            uptime_sec=int(now - start),
            started_at=started_at,
            tz=os.getenv("TZ", "Asia/Jakarta"),
        ), 200

def _import_dashboard_bp():
    """
    Import blueprint for dashboard (no silent fallback). Try known module names
    then raise error if not found so deploy fails fast with a clear traceback.
    """
    # Primary
    try:
        from satpambot.dashboard.webui import bp as dashboard_bp  # type: ignore
        return dashboard_bp
    except Exception as e_primary:
        # Secondary legacy name
        try:
            from satpambot.dashboard.app_dashboard import bp as dashboard_bp  # type: ignore
            return dashboard_bp
        except Exception as e_secondary:
            # Fail fast with helpful message
            raise ImportError(
                f"Dashboard blueprint not found. Tried satpambot.dashboard.webui and app_dashboard.\n"
                f"Errors: webui={e_primary!r}; app_dashboard={e_secondary!r}"
            )

def create_app() -> Flask:
    # Create Flask app bound to project templates/statics
    app = Flask(
        "satpambot_dashboard",
        template_folder=str(TPL),
        static_folder=str(STA),
        static_url_path="/static",
    )
    # Start time for /uptime and diagnostics
    app.config["START_TIME"] = time.time()

    # Basic config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-only-local")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024

    # Persisted uploads (Render Disk if mounted; else local data/)
    upload_base = Path(os.getenv("UPLOAD_DIR", "/var/data/uploads"))
    if not upload_base.exists():
        upload_base = ROOT / "data" / "uploads"
    upload_base.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_base)

    # Register dashboard blueprint (no fallback)
    dashboard_bp = _import_dashboard_bp()
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    # Health & uptime routes
    _wire_health(app)

    # Handy aliases
    _alias(app, "/",          "/dashboard/login")
    _alias(app, "/login",     "/dashboard/login")
    _alias(app, "/settings",  "/dashboard/settings")
    _alias(app, "/security",  "/dashboard/security")

    # Default timezone to WIB (can be overridden by environment)
    os.environ.setdefault("TZ", "Asia/Jakarta")

    log.info("[app] Flask ready. tpl=%s static=%s uploads=%s tz=%s",
             app.template_folder, app.static_folder, app.config["UPLOAD_FOLDER"], os.getenv("TZ"))
    return app

# Export WSGI app (Render/Gunicorn support)
app = create_app()
