from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

class SlashListBroadcast(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="broadcast_test")
    async def broadcast_test(self, ctx: commands.Context):
        # Fixed syntax: no semicolon before 'if'
        ch = getattr(ctx, "channel", None)
        if not ch:
            return
        await ctx.reply("Broadcast test OK", mention_author=False)

async def setup(bot):
    await bot.add_cog(SlashListBroadcast(bot))
