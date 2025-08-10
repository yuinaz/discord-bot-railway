# modules/discord_bot/events/bot_events.py

import logging
from modules.discord_bot.helpers.log_utils import announce_bot_online
from discord.ext import commands
from discord import Message

logger = logging.getLogger(__name__)

def register_basic_events(bot: commands.Bot):
    @bot.event
    async def on_ready():
        try:
            await announce_bot_online(bot.guilds[0] if bot.guilds else None, str(bot.user))
        except Exception:
            pass
        logger.info(f"✅ Bot terhubung sebagai {bot.user}")

    @bot.event
    async def on_message(message: Message):
        if message.author.bot:
            return
        from modules.discord_bot import message_handlers
        await message_handlers.handle_on_message(bot, message)
