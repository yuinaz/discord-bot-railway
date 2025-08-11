import logging
from modules.discord_bot import message_handlers
logger = logging.getLogger(__name__)

def register_advanced(bot):
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return
        try:
            await message_handlers.handle_on_message(bot, message)
        except Exception as e:
            logger.error(f"advanced_events pipeline error: {e}")
