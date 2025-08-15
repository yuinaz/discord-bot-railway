# Root app shim (for imports of `app`)
try:
    from dashboard.app import app, socketio  # type: ignore
except Exception:
    from satpambot.dashboard.app import app, socketio  # type: ignore
