import logging, threading, asyncio
from app import app
from satpambot.bot.modules.discord_bot.shim_runner import start_bot

log = logging.getLogger("entry.main")

def _run_web():
    log.info("🌐 Serving web on 0.0.0.0:10000")
    app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)

def main():
    logging.basicConfig(level=logging.INFO)
    t = threading.Thread(target=_run_web, name="web", daemon=True)
    t.start()
    log.info("Web is ready on port 10000")
    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
