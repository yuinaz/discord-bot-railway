
# sitecustomize.py
# Auto-imported by Python at startup if this directory is on sys.path.
# Silences noisy /healthz (also /health, /ping) access logs across Werkzeug/Gunicorn.
import logging

def _install_health_log_filter():
    try:
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        pass  # never break app on logging issues

def _monkeypatch_werkzeug_handler():
    try:
        from werkzeug.serving import WSGIRequestHandler as _WRH
        _orig = _WRH.log_request
        def _silent_health(self, *args, **kwargs):
            rl = getattr(self, "requestline", "") or ""
            if "/healthz" in rl or "/health" in rl or "/ping" in rl:
                return
            return _orig(self, *args, **kwargs)
        _WRH.log_request = _silent_health
    except Exception:
        pass

_install_health_log_filter()
_monkeypatch_werkzeug_handler()
