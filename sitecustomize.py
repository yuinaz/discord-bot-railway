# Silence noisy access logs for health endpoints
import logging
class _F(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
logging.getLogger("werkzeug").addFilter(_F())
logging.getLogger("gunicorn.access").addFilter(_F())

# === Render-like keepalive (guarded) ===
try:
    import os, threading, sys
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

            # Robust detection: if user runs `python main.py` / `python app.py`, DON'T start keepalive
            _argv = [os.path.basename(x).lower() for x in sys.argv if isinstance(x, str)]
            _is_main = any(x in ("main.py", "app.py") for x in _argv)
            if not _is_main:
                threading.Thread(target=_run, name="render-keepalive", daemon=True).start()
                print(f"[keepalive] listening on 0.0.0.0:{_PORT}", flush=True)
            else:
                print("[keepalive] skip (argv main.py/app.py detected)", flush=True)
        except Exception as _e:
            print(f"[keepalive] init failed (sitecustomize): {_e}", flush=True)
except Exception as _outer_e:
    print(f"[keepalive] skipped: {_outer_e}", flush=True)

# === Metrics ingest stub (append-only) ===
try:
    import os as _os
    _INGEST = _os.environ.get("METRICS_INGEST_STUB", "1") == "1"
    if _INGEST:
        try:
            from flask import Flask as _FApp, request
            _ms = _FApp("metrics-stub")
            @_ms.post("/api/metrics-ingest")
            def _ingest():
                try:
                    _ = request.get_json(silent=True)
                except Exception:
                    pass
                return ("", 204)

            class _QuietMetrics(logging.Filter):
                def filter(self, record):
                    try:
                        path = record.args[0] if isinstance(record.args, tuple) and record.args else ""
                    except Exception:
                        path = ""
                    return "/api/metrics-ingest" not in str(path)

            try:
                logging.getLogger("werkzeug").addFilter(_QuietMetrics())
                logging.getLogger("gunicorn.access").addFilter(_QuietMetrics())
            except Exception:
                pass
            print("[metrics-stub] /api/metrics-ingest ready (append-only)", flush=True)
        except Exception as _e:
            print(f"[metrics-stub] init failed: {_e}", flush=True)
    else:
        pass
except Exception as _outer_e:
    print(f"[metrics-stub] skipped: {_outer_e}", flush=True)
