"""
Flask entry for SatpamBot (single process friendly)
- Stable /healthz and /uptime (200)
- Quiet logs for health endpoints
- Registers dashboard web UI (blueprints, static alias, themes)
- NO watchdog that kills the process
"""
from __future__ import annotations
import os, time, logging
from typing import Optional, Tuple
from flask import Flask, jsonify, Response, redirect, request

_START_TS = time.time()

class _HealthAccessFilter(logging.Filter):
    SILENT = ("/healthz", "/uptime")
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        return not any(s in msg for s in self.SILENT)

def _probe_bot() -> Tuple[bool, Optional[int], Optional[int]]:
    # Best-effort probe: try to import shared state if available
    alive = False; guilds = None; latency_ms = None
    try:
        from satpambot.bot.modules.discord_bot import live_metrics  # type: ignore
        st = getattr(live_metrics, "STATE", None)
        if st and isinstance(st, dict):
            alive = bool(st.get("alive", False))
            guilds = st.get("guilds")
            latency_ms = st.get("latency_ms")
    except Exception:
        pass
    return alive, guilds, latency_ms

def create_app() -> Flask:
    app = Flask(__name__)
    # Set a trivial secret key if not present (needed by webui for session)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

    # Quiet werkzeug access log for health checks
    try:
        wz = logging.getLogger("werkzeug")
        wz.addFilter(_HealthAccessFilter())
        app.logger.addFilter(_HealthAccessFilter())
    except Exception:
        pass

    # ------------------- Basic routes -------------------
    @app.route("/healthz", methods=["GET", "HEAD"])
    def _healthz() -> Response:
        # HEAD should be enough for uptime monitors; always 200
        if request.method == "HEAD":
            return Response(status=200)
        return Response("ok", status=200, mimetype="text/plain")

    @app.route("/uptime", methods=["GET", "HEAD"])
    def _uptime():
        if request.method == "HEAD":
            return Response(status=200)
        now = time.time()
        return jsonify({
            "uptime_s": int(now - _START_TS),
            "pid": os.getpid(),
            "port": int(os.environ.get("PORT", "10000")),
            "ts": int(now)
        })

    # Root -> dashboard
    @app.route("/", methods=["GET"])
    def _root():
        return redirect("/dashboard", code=302)

    # Optional: surface bot liveness (503 if false)
    @app.get("/botlive")
    def _botlive():
        alive, guilds, latency_ms = _probe_bot()
        return jsonify({"alive": alive, "guilds": guilds, "latency_ms": latency_ms}), (200 if alive else 503)

    # ------------------- Register dashboard web UI -------------------
    try:
        from satpambot.dashboard.webui import register_webui_builtin  # type: ignore
        register_webui_builtin(app)
    except Exception as e:
        app.logger.warning("dashboard webui not registered: %s", e)

    return app

# WSGI entry for gunicorn or direct run
app = create_app()
