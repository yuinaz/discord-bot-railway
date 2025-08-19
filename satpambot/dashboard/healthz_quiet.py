import logging, time, os
DEFAULT_PATTERNS = ("GET /healthz ", "GET /favicon.ico ", "GET /uptime ")
class _SkipPaths(logging.Filter):
    def __init__(self, needles=DEFAULT_PATTERNS):
        super().__init__(); self.needles = tuple(needles or ())
    def filter(self, record: logging.LogRecord) -> bool:
        try: msg = record.getMessage()
        except Exception: return True
        return not any(n in msg for n in self.needles)

def silence_healthz_logs(extra_patterns=None):
    patterns = list(DEFAULT_PATTERNS)
    if extra_patterns: patterns.extend(extra_patterns)
    logger = logging.getLogger("werkzeug")
    logger.setLevel(logging.WARNING)
    for f in list(getattr(logger, "filters", [])):
        if isinstance(f, _SkipPaths): return
    logger.addFilter(_SkipPaths(patterns))

def ensure_healthz_route(app):
    if any(r.rule == "/healthz" for r in app.url_map.iter_rules()): return
    @app.get("/healthz")
    def _healthz(): return "OK", 200, {"Cache-Control": "no-store"}

def ensure_uptime_route(app):
    if any(r.rule == "/uptime" for r in app.url_map.iter_rules()): return
    app.config.setdefault("START_TIME", float(os.environ.get("START_TIME", time.time())))
    @app.get("/uptime")
    def _uptime():
        s = int(time.time() - float(app.config.get("START_TIME", time.time())))
        return f"UP {s}s", 200, {"Cache-Control": "no-store"}
