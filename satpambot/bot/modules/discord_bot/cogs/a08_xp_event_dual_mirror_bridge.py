from __future__ import annotations
import logging, os
from discord.ext import commands

log = logging.getLogger(__name__)

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d

class XpEventDualMirrorBridge(commands.Cog):
    """Guarantee pinned JSON staging updates on every XP event (redundant safety net)."""
    def __init__(self, bot):
        self.bot = bot
        self.total_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")

    async def _apply(self, delta: int):
        if not delta:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.stage_tracker import StageTracker
            kv = PinnedJSONKV(self.bot)
            tracker = StageTracker(kv, total_key=self.total_key)
            # read current total (kv fallback if resolver absent)
            try:
                from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import resolve_senior_total
                current_total = int(await resolve_senior_total() or 0)
            except Exception:
                m0 = await kv.get_map()
                current_total = _int(m0.get(self.total_key, 0), 0)
            new_total = current_total + int(delta)
            m = await tracker.add(int(delta))
            label = str(m.get("xp:stage:label"))
            cur = _int(m.get("xp:stage:current", 0), 0)
            req = _int(m.get("xp:stage:required", 1), 1)
            pct = float(m.get("xp:stage:percent", 0) or 0)
            await kv.set_multi({
                self.total_key: new_total,
                "learning:status": f"{label} ({pct}%)",
                "learning:status_json": {"label":label,"percent":pct,"remaining":max(0,req-cur),
                                         "senior_total":new_total,"stage":{"start_total": new_total - cur, "required": req, "current": cur}},
            })
            log.info("[xp-dual-bridge] delta=%s -> %s %s/%s (%s) total=%s", delta, label, cur, req, pct, new_total)
        except Exception as e:
            log.debug("[xp-dual-bridge] failed: %r", e)

    def _extract(self, *args, **kwargs) -> int:
        for k in ("amount","delta","xp","value"):
            if k in kwargs: return _int(kwargs.get(k), 0)
        if args: return _int(args[0], 0)
        return 0

    async def _handle(self, *a, **k):
        d = self._extract(*a, **k)
        if d: await self._apply(d)

    @commands.Cog.listener()
    async def on_xp_add(self, *a, **k):  await self._handle(*a, **k)

    @commands.Cog.listener()
    async def on_xp_award(self, *a, **k):  await self._handle(*a, **k)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *a, **k):  await self._handle(*a, **k)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpEventDualMirrorBridge(bot))
