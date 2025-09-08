
# Silence /healthz logs for Werkzeug/Gunicorn
import logging
class _F(logging.Filter):
    def filter(self, record):
        try: msg = record.getMessage()
        except Exception: msg = str(record.msg)
        return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
logging.getLogger("werkzeug").addFilter(_F())
logging.getLogger("gunicorn.access").addFilter(_F())

# === Render keepalive (no config change): open /healthz on $PORT ===
try:
    import os, threading
    _PORT = os.environ.get("PORT")
    if _PORT:
        try:
            from flask import Flask
            _ka = Flask(__name__)
            @_ka.get("/healthz")
            def _h():
                return "ok", 200
            def _run():
                _ka.run(host="0.0.0.0", port=int(_PORT), debug=False, threaded=True)
            threading.Thread(target=_run, name="render-keepalive", daemon=True).start()
            print(f"[keepalive] listening on 0.0.0.0:{_PORT}", flush=True)
        except Exception as _e:
            print(f"[keepalive] init failed: {_e}", flush=True)
except Exception as _e:
    pass
