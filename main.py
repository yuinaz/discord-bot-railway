import os
import eventlet
eventlet.monkey_patch()

from modules.discord_bot.helpers.env_loader import load_env
from app import app, socketio, bootstrap

if __name__ == "__main__":
    # Render kadang memberi PORT kosong -> fallback aman
    raw_port = os.getenv("PORT") or "8080"
    port = int(raw_port)

    # Inisialisasi DB, tema, sampler, dan broadcast loop
    bootstrap()

    # Jalankan via eventlet (bukan Werkzeug)
    socketio.run(app, host="0.0.0.0", port=port)
