import asyncio, logging, os, time, traceback
try:
    from .modules.discord_bot.shim_runner import start_bot
except Exception:
    from satpambot.bot.modules.discord_bot.shim_runner import start_bot  # type: ignore

logging.basicConfig(level=os.environ.get("LOG_LEVEL","INFO"))
log = logging.getLogger("satpambot.bot.main")

async def _run_once():
    await start_bot()

def main():
    backoff = 5  # seconds, doubles up to 60s
    while True:
        try:
            log.info("🤖 Starting Discord bot process...")
            asyncio.run(_run_once())
            log.warning("Bot returned gracefully; restarting in 3s...")
            time.sleep(3)
            backoff = 5  # reset backoff after clean return
        except Exception as e:
            log.error("Bot crashed: %s\n%s", e, traceback.format_exc())
            log.info("Restarting in %ss...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    main()
