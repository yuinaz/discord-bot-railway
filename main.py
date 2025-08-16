
import os
try:
    from dotenv import load_dotenv  # optional
    load_dotenv()
except Exception:
    pass

# Import Flask app
from satpambot.dashboard.app import app
try:
    from satpambot.dashboard.app import socketio  # optional
except Exception:
    socketio = None

# Optional: start Discord bot in background (RUN_BOT=1 and token provided)
def _start_bot_bg():
    import asyncio, threading
    token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
    if not token:
        return
    start = None
    try:
        from satpambot.bot.modules.discord_bot.discord_bot import start_bot as start
    except Exception:
        try:
            from satpambot.bot.modules.discord_bot.shim_runner import start_bot as start
        except Exception:
            start = None
    if not start:
        return
    async def _run():
        await start()
    try:
        asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())

if __name__ == "__main__":
    if os.getenv("RUN_BOT", "1") not in ("0", "false", "False"):
        import threading
        threading.Thread(target=_start_bot_bg, daemon=True).start()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    if socketio:
        socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)
    else:
        app.run(host=host, port=port)
