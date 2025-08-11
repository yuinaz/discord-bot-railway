import logging, asyncio
from modules.discord_bot.helpers.log_utils import upsert_status_embed, announce_bot_online

logger = logging.getLogger(__name__)

def setup_bot_events(bot):
    @bot.event
    async def on_ready():
        try:
            for g in bot.guilds:
                await upsert_status_embed(g, "✅ SatpamBot online dan siap berjaga.")
        except Exception:
            try:
                await announce_bot_online(bot.guilds[0] if bot.guilds else None, str(bot.user))
            except Exception:
                pass
        logger.info(f"✅ Bot terhubung sebagai {bot.user}")

    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        try:
            from modules.discord_bot import message_handlers
            await message_handlers.handle_on_message(bot, message)
        except Exception:
            pass
        try:
            await bot.process_commands(message)
        except Exception:
            pass
