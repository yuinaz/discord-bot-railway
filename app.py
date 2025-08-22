# app.py — ENTRY FLASK (dashboard)
from __future__ import annotations
import logging, os
from flask import Flask, redirect, Response

log = logging.getLogger("entry.app")

def _try_register_webui(app: Flask) -> None:
    tried = []
    for mod in ("satpambot.dashboard.webui", "dashboard.webui", "webui"):
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
    app.url_map.strict_slashes = False  # supaya /dashboard & /dashboard/ 200 tanpa 308
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "satpambot-secret")

    _ensure_healthz(app)
    _try_register_webui(app)

    # Pastikan /dashboard ada; kalau belum, aktifkan fallback (aman, tanpa ubah config)
    if not any(str(r.rule).startswith("/dashboard") for r in app.url_map.iter_rules()):
        _register_dashboard_blueprint_with_fallback(app)

    # >>> Tambahkan baris ini <<<
    _ensure_ui_api(app)
    # <<< Sampai sini >>>

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
                for token in ("/healthz", "/health", "/ping"):
                    if token in msg:
                        return False
                return True
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        pass

try:
    _install_health_log_filter(None)
except Exception:
    pass

def _register_dashboard_blueprint_with_fallback(app):
    """
    Daftarkan blueprint dashboard; fallback aktif jika import webui gagal.
    Tidak mengubah config/env lain. Jika webui utama tersedia, fallback tidak dipakai.
    """
    tried = []

    def _try(mod_name):
        mod = __import__(mod_name, fromlist=["bp", "register"])
        if hasattr(mod, "bp"):
            app.register_blueprint(getattr(mod, "bp")); return True
        if hasattr(mod, "register"):
            getattr(mod, "register")(app); return True
        return False

    # Urutan prioritas: webui utama -> fallback
    for mod_name in ("satpambot.dashboard.webui", "dashboard.webui", "webui", "satpambot.dashboard.app_fallback"):
        try:
            if _try(mod_name):
                return
        except Exception as e:
            tried.append(f"{mod_name}: {e.__class__.__name__}")

    # ---- Inline fallback sangat ringan ----
    # Catatan: strict_slashes=False supaya /dashboard (tanpa slash) TIDAK redirect ke /dashboard/
    from flask import Blueprint, render_template_string, redirect, url_for

    bp = Blueprint("dashboard_fallback", __name__, url_prefix="/dashboard", strict_slashes=False)

    # /dashboard dan /dashboard/ -> 200 (tanpa 308)
    @bp.route("/", methods=["GET"])
    @bp.route("", methods=["GET"])
    def _fb_home():
        return render_template_string(
            "<!doctype html><title>Dashboard</title>"
            "<p>Fallback dashboard aktif (WebUI utama gagal diimpor).</p>"
        ), 200

    # /dashboard/login dan /dashboard/login/ -> 200
    @bp.route("/login", methods=["GET"])
    @bp.route("/login/", methods=["GET"])
    def _fb_login_get():
        return render_template_string(
            "<!doctype html><title>Login</title>"
            "<form method='post'>"
            "<input name='username' placeholder='username' required>"
            "<input name='password' type='password' placeholder='password' required>"
            "<button type='submit'>Login</button></form>"
        ), 200

    # POST di /dashboard/login dan /dashboard/login/ -> redirect ke /dashboard (200)
    @bp.route("/login", methods=["POST"])
    @bp.route("/login/", methods=["POST"])
    def _fb_login_post():
        return redirect(url_for("dashboard_fallback._fb_home"))

    app.register_blueprint(bp)
    app.logger.warning("Dashboard webui gagal diimport; fallback blueprint aktif.")

def _ensure_ui_api(app):
    """Pastikan endpoint UI minimal tersedia untuk dashboard & smoketest."""
    def _has(rule: str) -> bool:
        try:
            return any(r.rule == rule for r in app.url_map.iter_rules())
        except Exception:
            return False

    # /api/ui-config
    if not _has("/api/ui-config"):
        @app.get("/api/ui-config")
        def _ui_config():
            # Nilai default aman; kalau kamu punya store/tema dinamis, silakan override di webui utama.
            theme = os.getenv("DASH_THEME", "gtake")
            return {
                "theme": theme,
                "accent": "teal",
                "bg_mode": "gradient",
                "logo_url": "/dashboard-static/logo.svg",
                # Flag fitur yang dashboard-mu baca:
                "activityChart": True,
                "dashDrop": True
            }

    # /api/ui-themes
    if not _has("/api/ui-themes"):
        @app.get("/api/ui-themes")
        def _ui_themes():
            # Daftar tema minimal; webui utama boleh menambah sendiri jika diperlukan.
            return {"themes": ["gtake"]}
