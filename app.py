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

# --- Append-only: harden routes for monobot (/, /uptime) ---
try:
    routes = {r.rule for r in app.url_map.iter_rules()}
    # Root (/) → redirect to dashboard/home jika ada, else 200 "ok"
    if "/" not in routes:
        from flask import redirect, url_for, Response
        @app.route("/", methods=["GET", "HEAD"])
        def __root__():
            try:
                return redirect(url_for("dashboard.home"))
            except Exception:
                return Response("ok", 200)

    # /uptime (GET/HEAD) → JSON uptime seconds
    if "/uptime" not in routes:
        import time
        _APP_START_TS = globals().get("_APP_START_TS")
        if _APP_START_TS is None:
            _APP_START_TS = time.time()
            globals()["_APP_START_TS"] = _APP_START_TS

        from flask import jsonify
        @app.route("/uptime", methods=["GET", "HEAD"])
        def __uptime__():
            return jsonify({"uptime_s": int(time.time() - _APP_START_TS)}), 200
except Exception:
    # jangan sampai crash kalau ada blueprint/route yang beda
    pass

