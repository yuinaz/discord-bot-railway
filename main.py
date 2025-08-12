# Monkey-patch must be before any Flask import
import os
try:
    import eventlet
    eventlet.monkey_patch()
    ASYNC_MODE = "eventlet"
except Exception:
    ASYNC_MODE = "threading"

from app import app, bootstrap  # import after monkey_patch

# Create SocketIO here (optional)
socketio = None
try:
    from flask_socketio import SocketIO
    socketio = SocketIO(app, async_mode=ASYNC_MODE)
except Exception as e:
    print("[main] Flask-SocketIO not available, fallback plain Flask:", e)
    socketio = None

if __name__ == "__main__":
    try:
        with app.app_context():
            bootstrap()
            print("[main] bootstrap() done.")
    except Exception as e:
        print("[main] bootstrap() error:", e)

    port = int(os.getenv("PORT") or "10000")
    host = "0.0.0.0"
    print(f"[main] starting on {host}:{port} (mode={ASYNC_MODE})")
    if socketio:
        socketio.run(app, host=host, port=port)
    else:
        app.run(host=host, port=port)
