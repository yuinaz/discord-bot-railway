from __future__ import annotations
import os
from flask import Flask, Response

# Import registrar from your package
from satpambot.dashboard.webui import register_webui_builtin

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

    # Register dashboard blueprints/endpoints
    register_webui_builtin(app)

    # Health endpoints for Render / any platform
    @app.route("/healthz", methods=["HEAD", "GET"])
    def _healthz():
        # Return 200 for both HEAD and GET
        return Response(status=200)

    @app.get("/uptime")
    def _uptime():
        return "ok", 200

    return app

# WSGI entrypoint for gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
