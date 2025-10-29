from __future__ import annotations
import logging, os, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)


def _extract_delta_and_user(*args, **kwargs):
    # Prefer explicit kwargs
    for k in ("amount","delta","xp","value"):
        if k in kwargs:
            try: return int(kwargs[k]), kwargs.get("user") or kwargs.get("member") or (args[0] if args else None)
            except Exception: pass
    # Common positional patterns: (user, delta [, reason]) or (delta, reason)
    if len(args) >= 2:
        try:
            amt = int(args[1]); return amt, args[0]
        except Exception: pass
    if len(args) >= 1:
        try:
            amt = int(args[0])
            if -100_000 <= amt <= 100_000: return amt, None
        except Exception: pass
    return 0, None

def _int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class XpEventDualMirrorBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.total_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")

    async def _apply(self, delta: int):
        if not delta or abs(delta) > 100_000:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.stage_tracker import StageTracker
            kv = PinnedJSONKV(self.bot); tracker = StageTracker(kv, total_key=self.total_key)
            try:
                from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import resolve_senior_total
                total0 = int(await resolve_senior_total() or 0)
            except Exception:
                m0 = await kv.get_map(); total0 = _int(m0.get(self.total_key, 0), 0)
            new_total = total0 + int(delta)
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

    async def _handle(self, *a, **k):
        d, _ = _extract_delta_and_user(*a, **k)
        if d: await self._apply(d)

    @commands.Cog.listener()
    async def on_xp_add(self, *a, **k): await self._handle(*a, **k)
    @commands.Cog.listener()
    async def on_xp_award(self, *a, **k): await self._handle(*a, **k)
    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *a, **k): await self._handle(*a, **k)

async def setup(bot: commands.Bot):
    res = bot.add_cog(XpEventDualMirrorBridge(bot))
    if asyncio.iscoroutine(res): await res
