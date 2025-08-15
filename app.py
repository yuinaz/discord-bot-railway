# Root app shim so imports of `app` work.
# It simply forwards to your dashboard module if present.
try:
    from dashboard.app import app, socketio  # type: ignore
except Exception:
    from satpambot.dashboard.app import app, socketio  # type: ignore
