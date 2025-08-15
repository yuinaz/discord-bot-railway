# main.py — entry script SatpamBot (mono)
# - Load .env files for local/dev
# - Start Flask dashboard
# - Start Discord bot automatically if token is present (unless RUN_BOT=0)

import os
import logging
import threading

# -------------------- ENV loader (local only; Render ignores) --------------------
try:
    from pathlib import Path
    from dotenv import load_dotenv  # pip install python-dotenv

    ROOT = Path(__file__).resolve().parent

    # base defaults
    f = ROOT / ".env"
    if f.exists():
        load_dotenv(f, override=False)

    # prod overrides (optional)
    if (os.getenv("ENV") or os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "").lower().startswith("prod"):
        f = ROOT / ".env.prod"
        if f.exists():
            load_dotenv(f, override=True)

    # local overrides (highest priority)
    f = ROOT / ".env.local"
    if f.exists():
        load_dotenv(f, override=True)
except Exception:
    # silent: keep running even if dotenv unavailable
    pass
# -------------------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOGLEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [entry] %(message)s",
)
log = logging.getLogger("entry")

def _configure_quiet_access_log():
    # QUIET_ACCESS_LOG=1 (default) menyembunyikan access log dari werkzeug/urllib3
    if (os.getenv('QUIET_ACCESS_LOG','1') != '0'):
        try:
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
            logging.getLogger('urllib3').setLevel(logging.ERROR)
        except Exception:
            pass



def get_flask_app():
    """Import dashboard Flask app; fallback to a tiny web if import fails."""
    try:
        from satpambot.dashboard.app import app as flask_app
        log.info("✅ Dashboard app loaded: satpambot.dashboard.app")
        return flask_app
    except Exception as e:
        log.exception("⚠️  Dashboard import failed, falling back to mini web: %s", e)
        from flask import Flask, jsonify, redirect

        app = Flask("mini-web")

        @app.get("/ping")
        def ping():
            return "pong", 200

        @app.get("/")
        def root():
            return redirect("/login", code=302)

        @app.get("/login")
        def login_stub():
            return jsonify(info="Dashboard unavailable (mini web)."), 503

        return app


def should_run_bot() -> bool:
    """
    Decide whether to run the bot:
    - RUN_BOT=0 / false / off => False
    - RUN_BOT=1 / true / on   => True
    - otherwise AUTO: True if DISCORD_TOKEN or BOT_TOKEN is present
    """
    v = (os.getenv("RUN_BOT") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return bool(os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN"))


def _run_supervisor():
    """Run the bot supervisor (blocking) inside a daemon thread."""
    try:
        from satpambot.bot.main import run_supervisor
        run_supervisor()
    except Exception:
        log.exception("Bot supervisor crashed")


def main():
    port = int(os.getenv("PORT", "10000"))
    log.info("ENTRY main.py start | RUN_BOT=%r | PORT=%s", os.getenv("RUN_BOT"), port)

    app = get_flask_app()

    
    _configure_quiet_access_log()
if should_run_bot():
        threading.Thread(target=_run_supervisor, name="bot-supervisor", daemon=True).start()
        log.info("🤖 Bot supervisor started in background")

    log.info("🌐 Starting Flask on 0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        log.error("SystemExit: %s", e)
        raise
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception:
        log.exception("Fatal error in main")
