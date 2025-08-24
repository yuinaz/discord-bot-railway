import os
from flask import Flask, Response
from satpambot.dashboard.webui import register_webui_builtin

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

    # Register all dashboard routes (/, /api/ui-*, /dashboard/*, etc.)
    register_webui_builtin(app)

    # Health endpoints for Render
    @app.route("/healthz", methods=["GET", "HEAD"])
    def _healthz():
        # Always return 200 for health check
        return Response(status=200)

    @app.route("/uptime", methods=["GET", "HEAD"])
    def _uptime():
        return Response(status=200)

    return app

# WSGI entry point
app = create_app()

# === APPEND-ONLY: alias /login -> /dashboard/login ===
try:
    from flask import redirect, url_for
    routes = {r.rule for r in app.url_map.iter_rules()}
    if "/login" not in routes:
        @app.get("/login")
        def __satp_login_alias():
            return redirect(url_for("dashboard.login"))
except Exception:
    pass
# === END ===

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
