import asyncio, logging, os
try:
    from .modules.discord_bot.shim_runner import start_bot
except Exception:
    from satpambot.bot.modules.discord_bot.shim_runner import start_bot  # type: ignore
logging.basicConfig(level=os.environ.get("LOG_LEVEL","INFO"))
if __name__ == "__main__":
    asyncio.run(start_bot())
