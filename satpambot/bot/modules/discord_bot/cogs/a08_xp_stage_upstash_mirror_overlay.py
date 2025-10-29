# satpambot/bot/modules/discord_bot/cogs/a08_xp_stage_upstash_mirror_overlay.py
from __future__ import annotations
import os, logging, asyncio, json
from urllib.parse import quote
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k, default=None):
    v = os.getenv(k)
    return v if v is not None else default

def _int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

def _extract_delta_and_user(*args, **kwargs):
    # Prefer explicit kwargs
    for k in ("amount","delta","xp","value"):
        if k in kwargs:
            try: return int(kwargs[k]), kwargs.get("user") or kwargs.get("member") or (args[0] if args else None)
            except Exception: pass
    # Positional patterns: (user, delta, ...), (delta, reason)
    if len(args) >= 2:
        try: return int(args[1]), args[0]
        except Exception: pass
    if len(args) >= 1:
        try:
            amt = int(args[0])
            if -100_000 <= amt <= 100_000: return amt, None
        except Exception: pass
    return 0, None

class XpStageUpstashMirrorOverlay(commands.Cog):
    """
    Mirror staged XP keys to Upstash on every XP event.
    Writes:
      - xp:stage:label/current/required/percent
      - learning:status
      - learning:status_json (as JSON string)
    Skips delta <= 0 or |delta| > 100k.
    """
    def __init__(self, bot):
        self.bot = bot
        # Upstash ENV
        self.url = _env("UPSTASH_REDIS_REST_URL","")
        self.token = _env("UPSTASH_REDIS_REST_TOKEN","")
        # Key names (override-able via ENV)
        self.k_stage_label   = _env("XP_STAGE_LABEL_KEY",   "xp:stage:label")
        self.k_stage_current = _env("XP_STAGE_CURRENT_KEY", "xp:stage:current")
        self.k_stage_req     = _env("XP_STAGE_REQUIRED_KEY","xp:stage:required")
        self.k_stage_pct     = _env("XP_STAGE_PERCENT_KEY", "xp:stage:percent")
        self.k_status        = "learning:status"
        self.k_status_json   = "learning:status_json"
        self.total_key       = _env("XP_SENIOR_KEY","xp:bot:senior_total")

    async def _upstash_set(self, key: str, value: str):
        if not self.url or not self.token:
            return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                # URL-encode key & value agar aman untuk endpoint path-based
                u = f"{self.url}/set/{quote(str(key), safe='')}/{quote(str(value), safe='')}"
                async with s.get(u, headers={"Authorization": f"Bearer {self.token}"} ) as r:
                    if r.status != 200:
                        txt = await r.text()
                        raise RuntimeError(f"HTTP {r.status}: {txt}")
        except Exception as e:
            log.debug("[xp-stage-upstash] set %s failed: %r", key, e)

    async def _apply(self, delta: int):
        if delta <= 0 or abs(delta) > 100_000:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.stage_tracker import StageTracker
            kv = PinnedJSONKV(self.bot)
            tracker = StageTracker(kv, total_key=self.total_key)
            # compute new stage using tracker.add (staging semantics)
            m = await tracker.add(int(delta))
            label = str(m.get("xp:stage:label"))
            cur = _int(m.get("xp:stage:current", 0), 0)
            req = _int(m.get("xp:stage:required", 1), 1)
            pct = float(m.get("xp:stage:percent", 0) or 0)
            status = f"{label} ({pct}%)"
            status_json = json.dumps({
                "label": label, "percent": pct, "remaining": max(0, req-cur),
                "senior_total": _int(m.get(self.total_key, 0), 0),
                "stage": {"start_total": _int(m.get("xp:stage:start_total", 0), 0),
                          "required": req, "current": cur}
            }, separators=(",",":"))
            # mirror to Upstash
            await asyncio.gather(
                self._upstash_set(self.k_stage_label,   label),
                self._upstash_set(self.k_stage_current, str(cur)),
                self._upstash_set(self.k_stage_req,     str(req)),
                self._upstash_set(self.k_stage_pct,     str(pct)),
                self._upstash_set(self.k_status,        status),
                self._upstash_set(self.k_status_json,   status_json),
            )
            log.info("[xp-stage-upstash] %s %s/%s (%.1f%%) -> mirrored", label, cur, req, pct)
        except Exception as e:
            log.debug("[xp-stage-upstash] apply failed: %r", e)

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
    await bot.add_cog(XpStageUpstashMirrorOverlay(bot))
