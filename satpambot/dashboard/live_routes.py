# -*- coding: utf-8 -*-
import time
from flask import jsonify
try:
    from satpambot.dashboard.discord_bridge import get_metrics
except Exception:
    get_metrics = None
START_TS = int(time.time())

def register_live_routes(app):
    @app.get("/api/ping")
    def api_ping():
        return jsonify({"ok": True, "ts": int(time.time()), "uptime_sec": int(time.time()-START_TS)})
    @app.get("/api/metrics")
    def api_metrics():
        if not get_metrics:
            return jsonify({"ok": False, "reason": "bridge_missing"}), 503
        data = get_metrics()
        return jsonify(data), (200 if data.get("ok") else 503)
