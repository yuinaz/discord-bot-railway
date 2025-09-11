from __future__ import annotations
from discord.ext import commands
import discord
class MessageEditRescan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after and not after.author.bot:
            self.bot.dispatch("message", after)
