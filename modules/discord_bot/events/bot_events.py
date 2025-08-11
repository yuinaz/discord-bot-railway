import logging, asyncio
from modules.discord_bot.helpers.log_utils import upsert_status_embed, announce_bot_online

logger = logging.getLogger(__name__)
STATUS_TEXT = "✅ SatpamBot online dan siap berjaga."

def setup_bot_events(bot):
    @bot.event
    async def on_ready():
        # Run once per process
        if getattr(bot, "_status_hb_started", False):
            return
        bot._status_hb_started = True

        # Small delay to ensure caches ready
        await asyncio.sleep(2)

        # Upsert status in all guilds (single embed per guild)
        try:
            for g in bot.guilds:
                await upsert_status_embed(g, STATUS_TEXT)
        except Exception:
            try:
                await announce_bot_online(bot.guilds[0] if bot.guilds else None, str(bot.user))
            except Exception:
                pass

        logger.info(f"✅ Bot terhubung sebagai {bot.user}")

        # Heartbeat: update same embed every 10 minutes
        async def _heartbeat():
            while True:
                try:
                    for g in bot.guilds:
                        await upsert_status_embed(g, STATUS_TEXT)
                except Exception:
                    pass
                await asyncio.sleep(600)
        bot.loop.create_task(_heartbeat())

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        # Jalankan pipeline handler
        try:
            from modules.discord_bot import message_handlers
            await message_handlers.handle_on_message(bot, message)
        except Exception:
            pass
        # PENTING: JANGAN panggil process_commands di sini,
        # biarkan cog PrefixGuard yang memanggilnya supaya tidak double.
