import os, time, logging
from flask import Flask, Response, jsonify, request
from satpambot.dashboard.webui import register_webui_builtin

class _HealthPathFilter(logging.Filter):
    SILENT_PATHS = {"/healthz", "/uptime"}
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(getattr(record, "msg", ""))
        for p in self.SILENT_PATHS:
            if p in msg:
                return False
        return True

class _RateLimitFilter(logging.Filter):
    def __init__(self, max_per_window=20, window_seconds=60):
        super().__init__()
        self.max = max_per_window
        self.win = window_seconds
        self.state = {}  # key -> [count, window_start]
    def filter(self, record):
        key = (record.name, getattr(record, "levelno", 20), str(getattr(record, "msg",""))[:120])
        now = int(time.time())
        cnt, start = self.state.get(key, (0, now))
        if now - start >= self.win:
            cnt, start = 0, now
        cnt += 1
        self.state[key] = (cnt, start)
        return cnt <= self.max

def _apply_quiet_logging(app: Flask):
    # Silence werkzeug access logs for health paths & rate-limit spam
    wlog = logging.getLogger("werkzeug")
    wlog.addFilter(_HealthPathFilter())
    wlog.addFilter(_RateLimitFilter(max_per_window=30, window_seconds=60))
    # Tone down noisy libraries
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

    try:
        register_webui_builtin(app)
    except Exception:
        pass

    @app.route("/healthz", methods=["GET", "HEAD"])
    def _healthz():
        return Response("OK", mimetype="text/plain", status=200)

    _APP_START_TS = time.time()

    # === IMPORTANT: keep /uptime semantics STABLE (always 200) ===
    @app.route("/uptime", methods=["GET", "HEAD"])
    def __uptime__():
        return jsonify({"uptime_s": int(time.time() - _APP_START_TS)}), 200

    # optional ops-only endpoint (not used by monitors)
    @app.route("/botlive", methods=["GET"])
    def __botlive__():
        ok = False
        payload = {"alive": False, "guilds": 0, "latency_ms": None}
        try:
            from satpambot.bot.modules.discord_bot import discord_bot as dmod
            bot = getattr(dmod, "bot", None)
            if bot is not None:
                alive = not (bot.is_closed() if hasattr(bot, "is_closed") else False)
                guilds = len(getattr(bot, "guilds", []))
                latency = getattr(bot, "latency", 0.0) or 0.0
                payload.update({"alive": bool(alive), "guilds": int(guilds), "latency_ms": int(latency * 1000)})
                ok = bool(alive)
        except Exception as e:
            payload["error"] = str(e)
        return jsonify(payload), (200 if ok else 503)

    _apply_quiet_logging(app)
    return app
