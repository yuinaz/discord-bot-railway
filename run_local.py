# run_local.py — local launcher for SatpamBot (token-force edition)
# - Picks DISCORD_BOT_TOKEN_LOCAL automatically
# - Mirrors to BOT_TOKEN / DISCORD_TOKEN / DISCORD_BOT_TOKEN
# - Injects token into modules.discord_bot.helpers.env.BOT_TOKEN if needed
# - Ctrl+C exits cleanly; --threading to avoid eventlet quirks
import os, sys, threading, argparse, signal

FORCE_THREADING = ("--threading" in sys.argv)

try:
    from modules.discord_bot.helpers.env_loader import load_env  # type: ignore
    profile = load_env()
    print(f"[run_local] ENV profile: {profile} (.env.local loaded if present)")
except Exception:
    pass

# ---- Token alias (and mirror) ----
src = (
    os.getenv("DISCORD_BOT_TOKEN_LOCAL")
    or os.getenv("DISCORD_BOT_TOKEN")
    or os.getenv("BOT_TOKEN")
    or os.getenv("DISCORD_TOKEN")
)
if src:
    for k in ("BOT_TOKEN", "DISCORD_TOKEN", "DISCORD_BOT_TOKEN"):
        if not os.getenv(k):
            os.environ[k] = src

def _inject_token_into_bot_env():
    """Some legacy code reads modules.discord_bot.helpers.env.BOT_TOKEN at import-time.
    Ensure it's populated even if their loader ignored env vars."""
    try:
        tok = os.getenv("BOT_TOKEN") or os.getenv("DISCORD_TOKEN") or os.getenv("DISCORD_BOT_TOKEN")
        import modules.discord_bot.helpers.env as benv  # type: ignore
        if not getattr(benv, "BOT_TOKEN", "") and tok:
            benv.BOT_TOKEN = tok
            print("[run_local] injected token into helpers.env.BOT_TOKEN")
    except Exception:
        pass

os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("DB_PATH", "superadmin.db")
os.environ.setdefault("GUILD_METRICS_ID", "761163966030151701")

def _graceful_exit(signum, frame):
    print(f"[run_local] received signal {signum}, shutting down...")
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)

for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
    if sig is not None:
        try:
            signal.signal(sig, _graceful_exit)
        except Exception:
            pass

ASYNC_MODE = "eventlet"
if os.name == 'nt':
    ASYNC_MODE = 'threading'  # windows-friendly
if FORCE_THREADING or os.getenv("SOCKETIO_MODE", "").lower() == "threading":
    ASYNC_MODE = "threading"

if ASYNC_MODE == "eventlet":
    try:
        import eventlet  # type: ignore
        eventlet.monkey_patch()
    except Exception:
        ASYNC_MODE = "threading"

from app import app, bootstrap  # noqa: E402

socketio = None
try:
    from flask_socketio import SocketIO, join_room, leave_room  # type: ignore
    socketio = SocketIO(app, async_mode=ASYNC_MODE, cors_allowed_origins="*")
except Exception as e:
    print("[run_local] SocketIO init failed:", e)

def _wire_bot_bridge():
    try:
        from modules.discord_bot import set_flask_app  # type: ignore
        set_flask_app(app)
    except Exception:
        pass
    if socketio:
        try:
            from modules.discord_bot.discord_bot import set_socketio as _set_sio  # type: ignore
            _set_sio(socketio)
        except Exception:
            pass

if socketio:
    @socketio.on("join")
    def _on_join(data):
        try:
            room = (data or {}).get("room")
            if room: join_room(room)
        except Exception:
            pass

    @socketio.on("leave")
    def _on_leave(data):
        try:
            room = (data or {}).get("room")
            if room: leave_room(room)
        except Exception:
            pass

def _mask(val: str, keep: int = 6) -> str:
    if not val: return ""
    if len(val) <= keep: return "*" * len(val)
    return val[:keep] + "***" + val[-keep:]

def _print_env_summary():
    keys = ["START_BOT_IN_WEB","DB_PATH","GUILD_METRICS_ID","LOG_CHANNEL_ID","ASSET_WEBHOOK_URL","PORT","FLASK_ENV","BOT_TOKEN","DISCORD_TOKEN","DISCORD_BOT_TOKEN","SOCKETIO_MODE"]
    print("[env] effective:")
    for k in keys:
        v = os.getenv(k, "")
        if k in ("ASSET_WEBHOOK_URL","BOT_TOKEN","DISCORD_TOKEN","DISCORD_BOT_TOKEN"):
            v = _mask(v, 6)
        print(f"  - {k} = {v}")
    print(f"[env] ASYNC_MODE resolved = {ASYNC_MODE}")

def start_web():
    bootstrap()
    host = "0.0.0.0"; port = int(os.getenv("PORT", "8080"))
    print(f"[run_local] Web starting on http://127.0.0.1:{port}  (mode={ASYNC_MODE})")
    try:
        if socketio:
            socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True, debug=True, use_reloader=False)
        else:
            app.run(host=host, port=port, debug=True)
    except KeyboardInterrupt:
        _graceful_exit(signal.SIGINT, None)

def start_bot():
    print("[run_local] Starting Discord bot …")
    _inject_token_into_bot_env()
    try:
        from modules.discord_bot import run_bot  # type: ignore
        run_bot()
    except KeyboardInterrupt:
        _graceful_exit(signal.SIGINT, None)
    except Exception as e:
        print(f"[run_local] Bot exited with error: {e}")

def start_bot_background():
    _wire_bot_bridge()
    def _runner():
        _inject_token_into_bot_env()
        try:
            from modules.discord_bot import run_bot  # type: ignore
            run_bot()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print("[run_local] bot thread exited:", e)
    t = threading.Thread(target=_runner, daemon=True, name="bot-thread")
    t.start()
    print("[run_local] Bot thread started (if BOT_TOKEN is set).")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-only", action="store_true", help="Run Discord bot only (blocking)")
    ap.add_argument("--web-only", action="store_true", help="Run web dashboard only")
    ap.add_argument("--no-bot", action="store_true", help="Do not start bot in background when running both")
    ap.add_argument("--threading", action="store_true", help="Force Socket.IO threading mode (disable eventlet)")
    args = ap.parse_args()

    if args.bot_only and args.web_only:
        print("[run_local] --bot-only and --web-only cannot be used together.")
        sys.exit(2)

    if args.bot_only:
        _print_env_summary()
        start_bot(); return

    if args.web_only:
        _print_env_summary()
        start_web(); return

    if not args.no_bot:
        start_bot_background()
    _print_env_summary()
    start_web()

if __name__ == "__main__":
    main()
