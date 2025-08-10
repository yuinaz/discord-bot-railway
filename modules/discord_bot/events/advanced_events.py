# modules/discord_bot/events/advanced_events.py

import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

def register_advanced_events(bot: commands.Bot):
    @bot.event
    async def on_message_delete(message: discord.Message):
        if message.author.bot:
            return
        logger.info(f"🗑 Pesan dihapus dari {message.author}: {message.content}")

    @bot.event
    async def on_message_edit(before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        logger.info(f"✏️ Pesan dari {before.author} diedit:\nDari: {before.content}\nMenjadi: {after.content}")
