import os
from modules.discord_bot.helpers.env_loader import load_env
from app import app, socketio

if __name__ == "__main__":
    # Honor Render.com assigned port if present
    port = int(os.getenv("PORT", "8080"))
    # In local dev, allow Werkzeug via SocketIO runner
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True, debug=debug)
