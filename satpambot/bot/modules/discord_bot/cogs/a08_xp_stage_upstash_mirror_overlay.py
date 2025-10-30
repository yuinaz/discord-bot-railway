
from __future__ import annotations
import logging, asyncio, json
from discord.ext import commands

log = logging.getLogger(__name__)

def _int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class XpStageUpstashMirrorOverlay(commands.Cog):
    """Force mirror of pinned KULIAH/MAGANG stage only; ignore others completely."""
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        self.k_stage_label   = cfg_str("XP_STAGE_LABEL_KEY",   "xp:stage:label")
        self.k_stage_current = cfg_str("XP_STAGE_CURRENT_KEY", "xp:stage:current")
        self.k_stage_req     = cfg_str("XP_STAGE_REQUIRED_KEY","xp:stage:required")
        self.k_stage_pct     = cfg_str("XP_STAGE_PERCENT_KEY", "xp:stage:percent")
        self.k_status        = "learning:status"
        self.k_status_json   = "learning:status_json"
        self.total_key       = cfg_str("XP_SENIOR_KEY","xp:bot:senior_total")
        self._last_state     = None

    async def _upstash_set(self, k: str, v):
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            cli = UpstashClient(); await cli.cmd("SET", k, str(v))
        except Exception:
            pass

    async def _apply(self, delta: int):
        if delta <= 0 or abs(delta) > 100_000:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()

            label = str(m.get(self.k_stage_label) or "")
            cur = _int(m.get(self.k_stage_current, 0), 0)
            req = _int(m.get(self.k_stage_req, 1), 1)
            pct = float(m.get(self.k_stage_pct, 0) or 0.0)
            if not label.startswith(("KULIAH-","MAGANG")):
                # ignore non-KULIAH
                log.info("[xp-stage-upstash] ignore non-KULIAH label: %r", label)
                return

            state = (label, cur, req, round(pct,1))
            if self._last_state == state: return
            self._last_state = state

            status = f"{label} ({pct}%)"
            status_json = json.dumps({
                "label": label, "percent": pct, "remaining": max(0, req-cur),
                "senior_total": _int(m.get(self.total_key, 0), 0),
                "stage": {"start_total": _int(m.get("xp:stage:start_total", 0), 0),
                          "required": req, "current": cur}
            }, separators=(",",":"))
            await asyncio.gather(
                self._upstash_set(self.k_stage_label,   label),
                self._upstash_set(self.k_stage_current, str(cur)),
                self._upstash_set(self.k_stage_req,     str(req)),
                self._upstash_set(self.k_stage_pct,     str(pct)),
                self._upstash_set(self.k_status,        status),
                self._upstash_set(self.k_status_json,   status_json),
            )
            log.info("[xp-stage-upstash] FORCED %s %s/%s (%.1f%%) -> mirrored", label, cur, req, pct)
        except Exception as e:
            log.debug("[xp-stage-upstash] apply failed: %r", e)

    async def _handle(self, *a, **k):
        # derive delta quickly
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
    await bot.add_cog(XpStageUpstashMirrorOverlay(bot))
