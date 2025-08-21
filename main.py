import os, logging, threading, asyncio, inspect, time
from app import app  # ensures create_app() executed and /healthz is ready

log = logging.getLogger("satpambot.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

def _probe_and_run_bot():
    """Try a sequence of common bot starters to maximize compatibility."""
    tried = []

    def attempt(modpath, attr=None):
        tried.append(f"{modpath}{'.'+attr if attr else ''}")
        try:
            mod = __import__(modpath, fromlist=['*'])
            fn = None
            if attr:
                fn = getattr(mod, attr, None)
            else:
                for name in ("start_bot_background","start_bot","run_bot","run","main"):
                    if hasattr(mod, name) and callable(getattr(mod, name)):
                        fn = getattr(mod, name)
                        break
            if not fn:
                return False
            log.info("🤖 Starting bot via %s.%s", modpath, fn.__name__)
            if inspect.iscoroutinefunction(fn):
                asyncio.run(fn())
            else:
                fn()
            return True
        except Exception as e:
            log.warning("Bot starter failed for %s: %s", f"{modpath}.{attr or ''}", e)
            return False

    # 1) satpambot.bot.main (generic then attribute-specific)
    if attempt("satpambot.bot.main"):
        return
    for attr in ("start_bot_background","start_bot","run_bot","run","main"):
        if attempt("satpambot.bot.main", attr):
            return

    # 2) known shim
    if attempt("satpambot.bot.modules.discord_bot.shim_runner", "start_bot_background"):
        return

    log.error("Bot not started; tried: %s", ", ".join(tried))

def _start_bot_background():
    if os.getenv("RUN_BOT", "1").lower() in ("0","false","no"):
        log.info("RUN_BOT disabled; bot will not start.")
        return
    delay = float(os.getenv("BOT_START_DELAY_SEC", "1.5"))
    def runner():
        # Short delay lets Flask bind the port so Render health check passes fast
        time.sleep(delay)
        _probe_and_run_bot()
    t = threading.Thread(target=runner, name="discord-bot", daemon=True)
    t.start()
    log.info("🤖 Bot thread launched (delay=%.1fs)", delay)

if __name__ == "__main__":
    _start_bot_background()
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
