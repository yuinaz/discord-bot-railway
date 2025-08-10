import os
import eventlet
eventlet.monkey_patch()

from modules.discord_bot.helpers.env_loader import load_env
from app import app, socketio

if __name__ == "__main__":
    # Honor Render.com assigned port if present, fallback ke 8080 jika kosong
    raw_port = os.getenv("PORT") or "8080"
    port = int(raw_port)
    socketio.run(app, host="0.0.0.0", port=port)
