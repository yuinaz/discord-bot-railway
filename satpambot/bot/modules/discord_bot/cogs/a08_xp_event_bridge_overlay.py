
from __future__ import annotations
import logging
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str

log = logging.getLogger(__name__)

ENABLED = (cfg_str("XP_EVENT_BRIDGE_ENABLE", "0") in ("1","true","on","yes","True"))

class XpEventBridgeOverlay(commands.Cog):
    """Disabled by default to avoid duplicate INCR/mirror. Set XP_EVENT_BRIDGE_ENABLE=1 to re-enable."""
    def __init__(self, bot):
        self.bot = bot

    async def _handle(self, *a, **k):
        if not ENABLED:
            return
        # Original logic intentionally disabled by default.
        return

    @commands.Cog.listener()
    async def on_xp_add(self, *a, **k):
        await self._handle(*a, **k)

    @commands.Cog.listener()
    async def on_xp_award(self, *a, **k):
        await self._handle(*a, **k)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *a, **k):
        await self._handle(*a, **k)

async def setup(bot):
    await bot.add_cog(XpEventBridgeOverlay(bot))
