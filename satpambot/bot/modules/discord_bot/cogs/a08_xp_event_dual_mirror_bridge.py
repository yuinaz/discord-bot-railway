
from __future__ import annotations
import logging, asyncio, json
from discord.ext import commands

log = logging.getLogger(__name__)

def _int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class XpEventDualMirrorBridge(commands.Cog):
    """Force learning:status to KULIAH/MAGANG (from pinned KV). Any non-KULIAH label is ignored."""
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        self.total_key = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")
        self.k_stage_label   = cfg_str("XP_STAGE_LABEL_KEY",   "xp:stage:label")
        self.k_stage_current = cfg_str("XP_STAGE_CURRENT_KEY", "xp:stage:current")
        self.k_stage_req     = cfg_str("XP_STAGE_REQUIRED_KEY","xp:stage:required")
        self.k_stage_pct     = cfg_str("XP_STAGE_PERCENT_KEY", "xp:stage:percent")

    async def _apply(self, delta: int):
        if delta <= 0 or abs(delta) > 100_000:  # guard
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.stage_tracker import StageTracker
            kv = PinnedJSONKV(self.bot)
            tracker = StageTracker(kv, total_key=self.total_key)

            # read previous total
            try:
                from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import resolve_senior_total
                total0 = int(await resolve_senior_total() or 0)
            except Exception:
                m0 = await kv.get_map()
                total0 = _int(m0.get(self.total_key, 0), 0)
            new_total = total0 + int(delta)

            # advance tracker (but we'll TRUST pinned stage values)
            await tracker.add(int(delta))

            # force use pinned stage (KULIAH/MAGANG only)
            m = await kv.get_map()
            label = str(m.get(self.k_stage_label) or "")
            cur   = _int(m.get(self.k_stage_current, 0), 0)
            req   = _int(m.get(self.k_stage_req, 1), 1)
            pct   = float(m.get(self.k_stage_pct, 0) or 0.0)

            if not label.startswith(("KULIAH-","MAGANG")):
                # do not update learning:* if not KULIAH/MAGANG
                log.info("[xp-dual-bridge] ignore non-KULIAH label: %r", label)
                return

            status = f"{label} ({pct}%)"
            status_json = json.dumps({
                "label": label, "percent": pct, "remaining": max(0, req - cur),
                "senior_total": new_total,
                "stage": {"start_total": max(0, new_total - cur), "required": req, "current": cur}
            }, separators=(",",":"))

            await kv.set_multi({
                self.total_key: new_total,
                "learning:status": status,
                "learning:status_json": status_json,
            })
            log.info("[xp-dual-bridge] FORCED %s %s/%s (%.2f%%) total=%s", label, cur, req, pct, new_total)
        except Exception as e:
            log.debug("[xp-dual-bridge] apply failed: %r", e)

    async def _handle(self, *a, **k):
        # derive delta from common patterns
        d = 0
        if k and isinstance(k, dict):
            for kk in ("amount","delta","xp","value"):
                if kk in k:
                    try: d = int(k[kk]); break
                    except Exception: pass
        if not d and a:
            try: d = int(a[1] if len(a) >= 2 else a[0])
            except Exception: d = 0
        if d: await self._apply(d)

    @commands.Cog.listener()
    async def on_xp_add(self, *a, **k): await self._handle(*a, **k)

    @commands.Cog.listener()
    async def on_xp_award(self, *a, **k): return

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *a, **k): return

async def setup(bot: commands.Bot):
    await bot.add_cog(XpEventDualMirrorBridge(bot))
