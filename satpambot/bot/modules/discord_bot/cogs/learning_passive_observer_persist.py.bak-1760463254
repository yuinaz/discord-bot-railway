# Compat shim: keep import passing but reuse the new observer
from __future__ import annotations
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.cogs.learning_passive_observer import LearningPassiveObserver

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserver(bot))

def setup(bot: commands.Bot):
    try: bot.add_cog(LearningPassiveObserver(bot))
    except TypeError: pass
