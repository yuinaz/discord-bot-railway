import os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "satpambot"))
try:
    # prioritas: dashboard dengan socketio
    from dashboard.app import app, socketio
    port = int(os.getenv("PORT", "10000"))
    try:
        socketio.run(app, host="0.0.0.0", port=port)
    except Exception:
        app.run(host="0.0.0.0", port=port)
except Exception as e:
    print("[FATAL] Gagal start dashboard:", e)
    raise
