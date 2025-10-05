from __future__ import annotations
from discord.ext import commands

async def setup(bot: commands.Bot):
    from .anti_url_phish_guard import AntiUrlPhishGuard  # type: ignore
    await bot.add_cog(AntiUrlPhishGuard(bot))
