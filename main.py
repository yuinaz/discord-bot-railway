# --- MUST monkey_patch before importing Flask/Werkzeug/app ---
import os

try:
    import eventlet
    eventlet.monkey_patch()
    ASYNC_MODE = "eventlet"
except Exception:
    ASYNC_MODE = "threading"

from app import app, bootstrap  # import after monkey_patch

# Try to create SocketIO here (don't depend on app exporting it)
socketio = None
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, async_mode=ASYNC_MODE)
except Exception as e:
    print("[main] Flask-SocketIO not available, falling back to plain Flask:", e)
    socketio = None

if __name__ == "__main__":
    # Ensure application context for any DB/init work inside bootstrap()
    try:
        with app.app_context():
            bootstrap()
    except Exception as e:
        print("[main] bootstrap() error:", e)

    port = int(os.getenv("PORT") or "10000")  # guard empty string
    host = "0.0.0.0"

    if socketio:
        socketio.run(app, host=host, port=port)
    else:
        app.run(host=host, port=port)
