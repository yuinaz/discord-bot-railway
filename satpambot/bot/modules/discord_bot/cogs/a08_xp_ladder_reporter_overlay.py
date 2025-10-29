from __future__ import annotations
import logging, asyncio
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

class XpLadderReporterOverlay(commands.Cog):
    """Report current staged progress (per-level) using StageResolver/KV (not cumulative bands)."""
    def __init__(self, bot):
        self.bot = bot
        self._boot = False
        self._task = self._periodic()

    @tasks.loop(minutes=10.0)
    async def _periodic(self):
        try:
            label, pct, cur, req, total = await self._resolve()
            log.info("[xp-ladder] %s %5.1f%%  (%s/%s)  total=%s", label, pct, cur, req, total)
        except Exception as e:
            log.debug("[xp-ladder] periodic report failed: %r", e)

    @_periodic.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def _resolve(self):
        # prefer stage_preferred(), fallback to pinned KV
        label, percent, cur, req, total = "KULIAH-S1", 0.0, 0, 19000, 0
        try:
            from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_preferred, resolve_senior_total
            lbl, pct, meta = await stage_preferred()
            label = str(lbl); percent = float(pct)
            cur = int(meta.get("current", 0)); req = int(meta.get("required", 1))
            total = int(await resolve_senior_total() or 0)
            return label, percent, cur, req, total
        except Exception:
            pass
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot); m = await kv.get_map()
            label = str(m.get("xp:stage:label", label))
            percent = float(m.get("xp:stage:percent", percent))
            cur = int(m.get("xp:stage:current", cur)); req = int(m.get("xp:stage:required", req))
            total = int(m.get("xp:bot:senior_total", total))
        except Exception:
            pass
        return label, percent, cur, req, total

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._boot:
            self._boot = True
            # one-shot report on boot
            try:
                label, pct, cur, req, total = await self._resolve()
                log.info("[xp-ladder] %s %5.1f%%  (%s/%s)  total=%s", label, pct, cur, req, total)
            finally:
                if not self._periodic.is_running():
                    self._periodic.start()

async def setup(bot: commands.Bot):
    await bot.add_cog(XpLadderReporterOverlay(bot))
