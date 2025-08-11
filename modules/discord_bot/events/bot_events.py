import logging, asyncio
from modules.discord_bot.helpers.log_utils import upsert_status_embed, announce_bot_online

logger = logging.getLogger(__name__)

STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

def setup_bot_events(bot):
    @bot.event
    async def on_ready():
        # run once per process
        if getattr(bot, "_status_hb_started", False):
            return
        bot._status_hb_started = True

        # Small delay to ensure caches ready
        await asyncio.sleep(2)

        # 1) Immediately upsert status on every guild
        try:
            for g in bot.guilds:
                await upsert_status_embed(g, STATUS_TEXT)
        except Exception:
            # fallback: best-effort text if upsert fails
            try:
                await announce_bot_online(bot.guilds[0] if bot.guilds else None, str(bot.user))
            except Exception:
                pass

        logger.info(f"✅ Bot terhubung sebagai {bot.user}")

        # 2) Start background heartbeat that updates the SAME embed every 10 minutes
        async def _heartbeat():
            while True:
                try:
                    for g in bot.guilds:
                        await upsert_status_embed(g, STATUS_TEXT)
                except Exception:
                    pass
                await asyncio.sleep(600)  # 10 minutes

        bot.loop.create_task(_heartbeat())

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # optional pipeline
        try:
            from modules.discord_bot import message_handlers
            await message_handlers.handle_on_message(bot, message)
        except Exception:
            pass
        # ALWAYS forward to command parser so prefix works
        try:
            await bot.process_commands(message)
        except Exception:
            pass
