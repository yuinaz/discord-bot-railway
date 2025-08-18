# satpambot.dashboard.healthz_quiet
# Suppress noisy access logs for /healthz (and optionally /favicon.ico).
# Usage in app.py:
#   from satpambot.dashboard.healthz_quiet import silence_healthz_logs, ensure_healthz_route
#   silence_healthz_logs()
#   ensure_healthz_route(app)
import logging

DEFAULT_PATTERNS = ("GET /healthz ", "GET /favicon.ico ")

class _SkipPaths(logging.Filter):
    def __init__(self, needles=DEFAULT_PATTERNS):
        super().__init__()
        self.needles = tuple(needles or ())

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return not any(n in msg for n in self.needles)

def silence_healthz_logs(extra_patterns=None):
    patterns = list(DEFAULT_PATTERNS)
    if extra_patterns:
        patterns.extend(extra_patterns)
    logger = logging.getLogger("werkzeug")
    # avoid duplicate filters
    for f in list(getattr(logger, "filters", [])):
        if isinstance(f, _SkipPaths):
            return
    logger.addFilter(_SkipPaths(patterns))

def ensure_healthz_route(app):
    # Register a fast /healthz route returning 200 OK if not already present.
    if any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
        return
    @app.get("/healthz")
    def _healthz():
        return "ok", 200
