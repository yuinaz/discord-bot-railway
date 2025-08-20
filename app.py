# app.py — WSGI entrypoint (dipakai oleh main.py & Render)
from importlib import import_module
import os

def _load_real_app():
    # Prefer webui (ekspor app dari create_app), fallback ke app_dashboard
    for name in (
        "satpambot.dashboard.webui",
        "satpambot.dashboard.app_dashboard",
        "app_dashboard",
    ):
        try:
            mod = import_module(name)
            app = getattr(mod, "app", None) or (
                getattr(mod, "create_app", None) and mod.create_app()
            )
            if app:
                return app
        except Exception:
            continue
    return None

app = _load_real_app()

# Tambahan health/uptime jika modul tersedia (no-op kalau sudah ada)
try:
    from satpambot.dashboard.healthz_quiet import (
        silence_healthz_logs,
        ensure_healthz_route,
        ensure_uptime_route,
    )
    silence_healthz_logs()
    ensure_healthz_route(app)
    ensure_uptime_route(app)
except Exception:
    pass

# SocketIO tidak dipakai di free plan (biarkan None supaya main.py pakai app.run)
socketio = None

if __name__ == "__main__":
    try:
        app.logger.info(
            "Route map: %s", [str(r.rule) for r in app.url_map.iter_rules()]
        )
    except Exception:
        pass
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
