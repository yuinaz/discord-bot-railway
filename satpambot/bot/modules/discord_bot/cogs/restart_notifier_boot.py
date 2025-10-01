from __future__ import annotations

import asyncio
from discord.ext import commands

# Helper used here (installed as helper module)
from satpambot.bot.modules.discord_bot.helpers import restart_notifier as _rn

class RestartNotifierBoot(commands.Cog):
    """Edits 'Restarting…' marker after the bot is back online."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # finalize the previously posted notice (if any)
        try:
            await _rn.finalize_after_ready(self.bot)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(RestartNotifierBoot(bot))
