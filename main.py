import os, logging, threading, asyncio, inspect, time
from app import create_app

log = logging.getLogger("satpambot.main")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

def _start_bot_thread():
    if not os.getenv("RUN_BOT", "1").strip() or os.getenv("RUN_BOT", "1") in ("0","false","False","no","No"):
        log.info("RUN_BOT disabled; skipping bot thread.")
        return

    def runner():
        # Try various known entrypoints
        tried = []
        def _try(path, attr=None):
            tried.append(f"{path}{'.'+attr if attr else ''}")
            try:
                mod = __import__(path, fromlist=['*'])
                fn = None
                if attr:
                    fn = getattr(mod, attr, None)
                else:
                    # candidate names
                    for name in ("start_bot_background","start_bot","run_bot","run","main"):
                        if hasattr(mod, name) and callable(getattr(mod, name)):
                            fn = getattr(mod, name)
                            break
                if fn:
                    log.info("🤖 Starting bot via %s", f"{path}.{fn.__name__}")
                    if inspect.iscoroutinefunction(fn):
                        asyncio.run(fn())
                    else:
                        fn()
                    return True
            except Exception as e:
                log.warning("Bot starter failed for %s: %s", f"{path}.{attr or ''}", e, exc_info=False)
            return False

        # 1) satpambot.bot.main:<various>
        if _try("satpambot.bot.main"):
            return
        # 2) explicit attributes
        for attr in ("start_bot_background","start_bot","run_bot","run","main"):
            if _try("satpambot.bot.main", attr):
                return
        # 3) shim runner commonly present in this project
        if _try("satpambot.bot.modules.discord_bot.shim_runner","start_bot_background"):
            return

        log.error("Bot not started; tried: %s", ", ".join(tried))

    t = threading.Thread(target=runner, name="discord-bot", daemon=True)
    t.start()
    log.info("🤖 Bot thread launched (pid thread=%s)", t.name)

# Start web app
app = create_app()

if __name__ == "__main__":
    # Launch bot in background
    _start_bot_thread()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
