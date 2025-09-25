# main.py — hardened run loop & cleanup to avoid "Event loop is closed"
import asyncio, logging, time, sys, os
from satpambot.bot.modules.discord_bot.shim_runner import start_bot

log = logging.getLogger("entry.main")

async def _bot_once_async():
    # start and ensure clean shutdown of http session even on exceptions
    bot = None
    try:
        log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
        # let start_bot create the client and login internally
        await start_bot()
    finally:
        # Best-effort cleanup of discord http session to prevent "Unclosed client session"
        try:
            from discord import Client
            # If your start_bot exposes bot instance globally:
            bot = getattr(sys.modules.get("satpambot.bot.modules.discord_bot.shim_runner"), "BOT_INSTANCE", None)
        except Exception:
            bot = None
        if bot is not None:
            try:
                await bot.close()
            except Exception:
                pass
            try:
                http = getattr(bot, "http", None)
                session = getattr(http, "_HTTPClient__session", None)
                if session and not session.closed:
                    await session.close()
            except Exception:
                pass
        try:
            await asyncio.sleep(0)
            await asyncio.get_running_loop().shutdown_asyncgens()
        except Exception:
            pass

def main():
    backoff = 10
    while True:
        try:
            # Create a fresh loop explicitly to avoid policy/state leakage
            policy = asyncio.DefaultEventLoopPolicy()
            asyncio.set_event_loop_policy(policy)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_bot_once_async())
            # If _bot_once_async returns normally, break
            break
        except Exception as e:
            log.error("Bot crashed: %s", e, exc_info=True)
        finally:
            try:
                if not loop.is_closed():
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
            except Exception:
                pass
        log.info("Restarting in %ss...", backoff)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("🌐 Serving web on 0.0.0.0:10000")
    # web app init here if needed
    main()
