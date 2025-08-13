# modules/discord_bot/__init__.py
# Safe re-exports for external imports.
# We keep set_flask_app available to avoid ImportError across environments.

from .discord_bot import bot, run_bot

# Try to import set_flask_app if it exists; otherwise define a no-op to keep compatibility.
try:
    from .discord_bot import set_flask_app  # type: ignore
except Exception:
    def set_flask_app(app):  # fallback no-op
        pass


# socketio setter passthrough
try:
    from .discord_bot import set_socketio  # type: ignore
except Exception:
    def set_socketio(_):  # no-op fallback
        pass
