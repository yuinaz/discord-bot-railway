# run_local.py - start Flask+SocketIO app and/or Discord bot locally
import os, sys, threading, argparse
from modules.discord_bot.helpers.env_loader import load_env

os.environ.setdefault("ENV_PROFILE", "local")
profile = load_env()
print(f"[run_local] ENV profile: {profile} (.env.local loaded if present)")

os.environ.setdefault("FLASK_DEBUG", "1")
os.environ.setdefault("FLASK_ENV","development")

def start_web():
    # prevent app from auto-starting a bot if we only want web
    if os.getenv("WEB_ONLY") == "1":
        os.environ["DISABLE_APP_AUTOBOT"] = "1"
    from app import app, socketio, bootstrap
    bootstrap()
    port = int(os.getenv("PORT", "8080"))
    print(f"[run_local] Web starting on http://127.0.0.1:{port}")
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True, debug=True, use_reloader=False)

def start_bot():
    # run bot directly without importing app to avoid duplicate bot
    print("[run_local] Starting Discord bot …")
    try:
        from modules.discord_bot.discord_bot import run_bot
        run_bot()
    except Exception as e:
        print(f"[run_local] Bot exited with error: {e}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bot-only", action="store_true")
    ap.add_argument("--web-only", action="store_true")
    args = ap.parse_args()

    if args.bot_only and args.web_only:
        print("[run_local] --bot-only and --web-only cannot be used together.")
        sys.exit(2)

    if args.bot_only:
        # ensure the app won't autostart a bot if accidentally imported elsewhere
        os.environ["DISABLE_APP_AUTOBOT"] = "1"
        start_bot()
        return

    if args.web_only:
        os.environ["WEB_ONLY"] = "1"
        start_web()
        return

    # default: start web, but let app autostart bot internally once
    start_web()

if __name__ == "__main__":
    main()
