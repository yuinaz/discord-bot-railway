from __future__ import annotations
# Example updated to new StickyEmbed signature (no path argument)
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.sticky_embed import StickyEmbed

class PhishLogStickyExample(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sticky = StickyEmbed()

    @commands.command(name="phish_example")
    async def phish_example(self, ctx: commands.Context):
        msg = await self.sticky.ensure(ctx.channel, "Anti-Image Guard — Report (example)")
        emb = msg.embeds[0] if msg.embeds else discord.Embed(title="Anti-Image Guard — Report (example)")
        emb.description = (emb.description or "") + "\n• example: hello"
        await self.sticky.update(msg, emb)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishLogStickyExample(bot))

def setup(bot: commands.Bot):
    try: bot.add_cog(PhishLogStickyExample(bot))
    except TypeError: pass
