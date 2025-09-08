
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

# --- Append-only: stub metrics ingest (ADD ONLY, no config change) ---
try:
    _app_obj = None
    try:
        _app_obj = _app  # existing keepalive app name (variant)
    except NameError:
        pass
    try:
        if _app_obj is None:
            _app_obj = _ka  # other variant used earlier
    except NameError:
        pass

    if _app_obj is not None:
        try:
            from flask import request
            @_app_obj.post("/api/metrics-ingest")
            def __metrics_ingest__():
                try:
                    _ = request.get_json(silent=True)
                except Exception:
                    pass
                return ("", 204)

            @_app_obj.post("/api/metrics-ingest/bulk")
            def __metrics_ingest_bulk__():
                try:
                    _ = request.get_json(silent=True)
                except Exception:
                    pass
                return ("", 204)

            # quiet access log for these endpoints
            import logging
            class _QuietMetrics(logging.Filter):
                def filter(self, record):
                    try:
                        path = record.args[0] if isinstance(record.args, tuple) and record.args else ""
                        return "/api/metrics-ingest" not in str(path)
                    except Exception:
                        return True
            try:
                logging.getLogger("werkzeug").addFilter(_QuietMetrics())
                logging.getLogger("gunicorn.access").addFilter(_QuietMetrics())
            except Exception:
                pass
            print("[metrics-stub] /api/metrics-ingest ready (append-only)", flush=True)
        except Exception as _e:
            print(f"[metrics-stub] init failed: {_e}", flush=True)
    else:
        # tidak membuat server baru agar tidak konflik port — hanya append
        pass
except Exception as _outer_e:
    print(f"[metrics-stub] skipped: {_outer_e}", flush=True)

