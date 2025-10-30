
from __future__ import annotations
import logging, asyncio
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int, cfg_str

log = logging.getLogger(__name__)

BACKOFF = cfg_int("PASSIVE_TOTAL_OFFSET_BACKOFF_SEC", 180)
ENABLE  = cfg_str("PASSIVE_TOTAL_OFFSET_ENABLE", "1") in ("1","true","on","yes","True")

class PassiveTotalOffsetOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _refresh_once(self):
        if not ENABLE: return
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            us = UpstashClient()
            await us.cmd("GET", "xp:bot:senior_total")
        except Exception as e:
            log.warning("[passive-total-offset] refresh fail: %r (retry in %ss)", e, BACKOFF)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        while True:
            await self._refresh_once()
            await asyncio.sleep(BACKOFF)

async def setup(bot):
    await bot.add_cog(PassiveTotalOffsetOverlay(bot))
