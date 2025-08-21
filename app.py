import os
import time
import logging
from typing import Any, Optional

from flask import Flask, jsonify, redirect

logger = logging.getLogger("entry.app")
logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))

# --- helpers -----------------------------------------------------------------

def _ensure_dirs(app: Flask) -> None:
    up = app.config.setdefault("UPLOAD_FOLDER", os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads")))
    os.makedirs(up, exist_ok=True)
    if not os.getenv("TZ"):
        os.environ["TZ"] = os.getenv("APP_TZ", "Asia/Jakarta")


def _register_health_endpoints(app: Flask) -> None:
    @app.get("/healthz")
    def healthz():
        # minimal health endpoint for Render health-checks
        return "ok", 200

    @app.get("/uptime")
    def uptime():
        start = app.config.get("START_TIME", time.time())
        return jsonify(
            status="ok",
            uptime_sec=int(time.time() - start),
            started_at=int(start),
        )


def _safe_add_alias(app: Flask, rule: str, target: str, endpoint_name: str) -> None:
    # Avoid AssertionError by giving a unique endpoint name per alias
    def _go():
        return redirect(target, code=302)
    try:
        app.add_url_rule(rule, endpoint=endpoint_name, view_func=_go)
        logger.info("[alias] %s -> %s", rule, target)
    except Exception as e:
        logger.warning("Alias %s -> %s not installed: %s", rule, target, e)


def _try_register_dashboard_blueprint(app: Flask) -> bool:
    """
    Try best-effort import & register dashboard from your project.
    Returns True if at least one dashboard was registered.
    """
    tried = []
    # order matters: prefer webui first
    candidates = [
        ("satpambot.dashboard.webui", ("bp", "blueprint", "dashboard_bp", "app_bp")),
        ("satpambot.dashboard.app_dashboard", ("bp", "blueprint", "dashboard_bp", "app_bp")),
    ]

    for mod_name, attr_names in candidates:
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception as e:
            tried.append(f"{mod_name} (import error: {e})")
            continue

        # common patterns
        # 1) module exposes a Blueprint object
        for attr in attr_names:
            bp = getattr(mod, attr, None)
            if bp is not None:
                try:
                    app.register_blueprint(bp, url_prefix="/dashboard")
                    logger.info("[dashboard] blueprint registered from %s.%s", mod_name, attr)
                    return True
                except Exception as e:
                    tried.append(f"{mod_name}.{attr} (register error: {e})")

        # 2) module has init_app(app) or register(app)
        for fn_name in ("init_app", "register", "setup"):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                try:
                    fn(app)  # type: ignore
                    logger.info("[dashboard] %s.%s(app) executed", mod_name, fn_name)
                    return True
                except Exception as e:
                    tried.append(f"{mod_name}.{fn_name}(app) (error: {e})")

    logger.error("No dashboard blueprint registered. Tried: %s", " | ".join(tried))
    return False


def create_app() -> Flask:
    """
    Unified app factory for Render. Guarantees:
    - /healthz always 200 OK
    - /uptime JSON
    - Dashboard blueprint registered when available (no plain-string fallback)
    - Safe route aliases that won't overwrite endpoints
    """
    app = Flask("satpambot_dashboard")
    app.config["START_TIME"] = time.time()
    _ensure_dirs(app)
    _register_health_endpoints(app)

    # load dashboard
    ok = _try_register_dashboard_blueprint(app)
    if not ok:
        # hard fail (so logs show root cause) but still keep /healthz alive
        logger.error("Dashboard failed to load - check import errors above.")

    # route aliases (do NOT override if already exists)
    _safe_add_alias(app, "/", "/dashboard", endpoint_name="_alias_root")
    _safe_add_alias(app, "/login", "/dashboard/login", endpoint_name="_alias_login")
    _safe_add_alias(app, "/settings", "/dashboard/settings", endpoint_name="_alias_settings")
    _safe_add_alias(app, "/security", "/dashboard/security", endpoint_name="_alias_security")

    return app


# expose for main.py
try:
    app: Flask = create_app()
except Exception as e:
    # We still want /healthz to be available if create_app blows up.
    logging.exception("create_app failed: %s", e)
    _fallback = Flask("fallback")
    _fallback.config["START_TIME"] = time.time()

    @_fallback.get("/healthz")
    def _h():
        return "ok", 200

    @_fallback.get("/uptime")
    def _u():
        start = _fallback.config.get("START_TIME", time.time())
        return jsonify(status="degraded", uptime_sec=int(time.time() - start), started_at=int(start))

    app = _fallback  # type: ignore
    logger.warning("[app] running in degraded mode; only /healthz & /uptime available")
