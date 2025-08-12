
import os

try:
    # Prefer using socketio exported by app.py if available
    from app import app, socketio, bootstrap
except Exception:
    # Fallback: import app + bootstrap, then create SocketIO instance here
    from app import app, bootstrap
    socketio = None
    try:
        from flask_socketio import SocketIO
        try:
            import eventlet
            eventlet.monkey_patch()
            ASYNC_MODE = "eventlet"
        except Exception:
            ASYNC_MODE = "threading"
        socketio = SocketIO(app, async_mode=ASYNC_MODE)
    except Exception as e:
        print("[main] SocketIO fallback failed:", e)
        socketio = None

if __name__ == "__main__":
    # Ensure DB/tables etc.
    try:
        bootstrap()
    except Exception as e:
        print("[main] bootstrap() error:", e)

    port = int(os.getenv("PORT", "10000"))
    host = "0.0.0.0"
    if socketio:
        socketio.run(app, host=host, port=port)
    else:
        # Plain Flask fallback if SocketIO is unavailable
        app.run(host=host, port=port)
