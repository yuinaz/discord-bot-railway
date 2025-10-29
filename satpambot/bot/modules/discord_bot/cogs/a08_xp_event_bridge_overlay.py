from __future__ import annotations
import logging, os, json, urllib.request
from typing import Optional, Any
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d

def _xp_key() -> str:
    return _env("XP_TOTAL_KEY","xp:bot:senior_total") or "xp:bot:senior_total"

def _pipe(cmds: list[list[str]]) -> Optional[list[dict]]:
    base = _env("UPSTASH_REDIS_REST_URL"); tok = _env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: 
        log.warning("[xp-bridge] Upstash not configured; skip INCR")
        return None
    body = json.dumps(cmds).encode("utf-8")
    req = urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=4.0) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def _coerce_amount(*args, **kwargs) -> int:
    # look into kwargs
    for k in ("amount","delta","xp","value","points","score"):
        if k in kwargs:
            try: return int(kwargs[k])
            except Exception: pass
    # positional
    for a in args:
        try:
            return int(a)
        except Exception:
            continue
    return 0

class XpEventBridgeOverlay(commands.Cog):
    """
    Convert dispatched XP events into ladder total increments.
    Listened events:
      - xp_add            -> def on_xp_add(...)
      - xp.award          -> @listener(name='xp.award')
      - satpam_xp         -> @listener(name='satpam_xp')
    """
    def __init__(self, bot):
        self.bot = bot
        log.info("[xp-bridge] overlay ready; key=%s", _xp_key())

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        await self._handle_event("xp_add", *args, **kwargs)

    @commands.Cog.listener(name='xp.award')
    async def _on_xp_award(self, *args, **kwargs):
        await self._handle_event("xp.award", *args, **kwargs)

    @commands.Cog.listener(name='satpam_xp')
    async def _on_satpam_xp(self, *args, **kwargs):
        await self._handle_event("satpam_xp", *args, **kwargs)

    async def _handle_event(self, evt: str, *args, **kwargs):
        amt = _coerce_amount(*args, **kwargs)
        rsn = kwargs.get("reason") or kwargs.get("tag") or kwargs.get("why") or ""
        if not isinstance(amt, int) or amt == 0:
            log.debug("[xp-bridge] %s ignored (amt=0) args=%r kwargs=%r", evt, args, kwargs)
            return
        key = _xp_key()
        try:
            r = _pipe([["INCRBY", key, str(int(amt))]])
            if isinstance(r, list) and len(r)>0 and isinstance(r[0], dict) and "error" in r[0]:
                log.warning("[xp-bridge] %s INCR err: %s", evt, r[0]["error"])
            else:
                log.info("[xp-bridge] %s +%s (%s) -> %s", evt, amt, rsn, key)
        except Exception as e:
            log.warning("[xp-bridge] %s failed: %r", evt, e)

async def setup(bot):
    await bot.add_cog(XpEventBridgeOverlay(bot))