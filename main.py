import os
import time
import logging
import importlib
import threading

from werkzeug.serving import is_running_from_reloader

logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))
log = logging.getLogger("entry.main")

# Create Flask app first so Render health-check can succeed
try:
    from app import create_app
    flask_app = create_app()
    log.info("[web] Flask app created via create_app()")
except Exception as e:
    log.warning("create_app() failed (%s), try importing fallback 'app' variable", e)
    from app import app as flask_app  # type: ignore
    log.info("[web] Flask app imported as 'app'")

PORT = int(os.getenv("PORT", "10000"))
HOST = os.getenv("HOST", "0.0.0.0")


def _start_bot_background():
    if os.getenv("RUN_BOT", "1") in ("0", "false", "False", "no", "NO"):
        log.info("[bot] RUN_BOT disabled; web-only mode")
        return

    starters = [
        ("satpambot.bot.main", "start_bot_background"),
        ("satpambot.bot.main", "start_bot"),
        ("satpambot.bot.main", "run_bot"),
        ("satpambot.bot.main", "run"),
        ("satpambot.bot.main", "main"),
        ("satpambot.bot.modules.discord_bot.shim_runner", "start_bot_background"),
    ]
    last_err = None
    for mod_name, fn_name in starters:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                t = threading.Thread(target=fn, name="DiscordBot", daemon=True)
                t.start()
                log.info("🤖 Bot started in background thread using %s.%s", mod_name, fn_name)
                return
            else:
                last_err = f"{mod_name}.{fn_name} not callable/exists"
        except Exception as e:
            last_err = f"{mod_name}.{fn_name} -> {e}"

    log.warning("[bot] Not started: %s", last_err or "no starter found")


if __name__ == "__main__":
    # delay bot start a bit to ensure port is bound early for health-checks
    delay = float(os.getenv("BOT_START_DELAY_SEC", "1.5"))
    threading.Timer(delay, _start_bot_background).start()
    log.info("🌐 Serving web on %s:%s", HOST, PORT)
    # Do not double-run the bot thread under reloader in dev
    flask_app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
