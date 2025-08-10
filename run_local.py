# run_local.py - start Flask+SocketIO app and Discord bot in local mode
import os
from modules.discord_bot.helpers.env_loader import load_env

# Force local profile to load .env.local (but don't override env already set)
os.environ.setdefault("ENV_PROFILE", "local")
profile = load_env()
print(f"[run_local] ENV profile: {profile} (.env.local loaded if present)")

# Optional debug flags
os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("FLASK_ENV","development")

# Start the Flask-SocketIO app
from app import app, socketio  # app creates bot background threads on import

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"[run_local] Starting on http://127.0.0.1:{port}")
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True, debug=True)
