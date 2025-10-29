from __future__ import annotations
import logging, os, json, urllib.request, re
from typing import Optional, Any
from discord.ext import commands

log = logging.getLogger(__name__)

def _smart_coerce(raw):
    try:
        j = json.loads(raw)
        if isinstance(j,(int,float)): return int(j)
        if isinstance(j,str) and re.fullmatch(r"[-+]?\d+", j): return int(j)
        if isinstance(j,dict):
            for k in ("senior_total","total","xp","amount","value"):
                v = j.get(k)
                if isinstance(v,(int,float)): return int(v)
                if isinstance(v,str) and re.fullmatch(r"[-+]?\d+", v): return int(v)
    except Exception: 
        pass
    ints = re.findall(r"[-+]?\d+", str(raw))
    if ints:
        ints.sort(key=lambda s: (len(s.lstrip("+-")), int(s)), reverse=True)
        return int(ints[0])
    return 0

def _coerce_key_numeric(key: str) -> bool:
    r = _pipe([["GET", key]])
    try:
        raw = r[0].get("result")
    except Exception:
        raw = None
    if raw is None:
        return bool(_pipe([["SET", key, "0"]]))
    val = _smart_coerce(raw)
    return bool(_pipe([["SET", key, str(val)]]))



def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d

def _xp_key() -> str:
    return _env("XP_TOTAL_KEY","xp:bot:senior_total") or "xp:bot:senior_total"

def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok:
        log.warning("[xp-bridge] Upstash not configured; skip INCR")
        return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=4.0) as r:
        import json as _j; return _j.loads(r.read().decode("utf-8","ignore"))

_num = re.compile(r'^[\s]*([+-]?\d+)')

def _parse_num(x) -> Optional[int]:
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    m=_num.match(str(x))
    if not m: return None
    try: return int(m.group(1))
    except Exception: return None

def _looks_like_discord_id(n: int) -> bool:
    try: return int(n) >= 10**12
    except Exception: return False

def _coerce_amount_from_args(args) -> Optional[int]:
    if not args: return None
    nums = []
    for a in args:
        # object with id
        if hasattr(a, "id"):
            nums.append(_parse_num(a.id))
        else:
            nums.append(_parse_num(a))
    nums = [n for n in nums if isinstance(n,int)]
    if not nums: return None
    if len(nums) >= 2 and _looks_like_discord_id(nums[0]):
        return nums[1]
    pos = [n for n in nums if n>0]
    if pos:
        return sorted(pos, key=abs)[0]
    return nums[0]

def _clamp(n: int) -> int:
    try: lim = int(_env("XP_EVENT_MAX_ABS","10000"))
    except Exception: lim = 10000
    if n > lim: log.warning("[xp-bridge] clamp %s -> %s", n, lim); return lim
    if n < -lim: log.warning("[xp-bridge] clamp %s -> -%s", n, lim); return -lim
    return n

class XpEventBridgeOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("[xp-bridge] ready; key=%s", _xp_key())

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        await self._handle("xp_add", *args, **kwargs)

    @commands.Cog.listener(name="xp.award")
    async def _on_award(self, *args, **kwargs):
        await self._handle("xp.award", *args, **kwargs)

    @commands.Cog.listener(name="satpam_xp")
    async def _on_satpam(self, *args, **kwargs):
        await self._handle("satpam_xp", *args, **kwargs)

    async def _handle(self, evt, *args, **kwargs):
        amt = None
        for k in ("amount","delta","xp","value","points","score"):
            if k in kwargs:
                v = _parse_num(kwargs[k])
                if isinstance(v,int): amt = v; break
        if amt is None:
            amt = _coerce_amount_from_args(args)
        if not isinstance(amt, int) or amt == 0:
            log.debug("[xp-bridge] %s ignored amt=%r args=%r kwargs=%r", evt, amt, args, kwargs)
            return
        amt = _clamp(amt)
        r = _pipe([["INCRBY", _xp_key(), str(amt)]])
        if r and isinstance(r,list) and len(r)>0 and "error" in r[0]:
            log.warning("[xp-bridge] %s INCR err: %s (amt=%s)", evt, r[0]["error"], amt)
            if _coerce_key_numeric(_xp_key()):
                r2 = _pipe([["INCRBY", _xp_key(), str(amt)]])
                if r2 and isinstance(r2,list) and len(r2)>0 and "error" in r2[0]:
                    log.warning("[xp-bridge] retry failed: %s", r2[0]["error"])
                else:
                    why = kwargs.get("reason") or kwargs.get("tag") or kwargs.get("why") or ""
                    log.info("[xp-bridge] %s +%s (%s) -> %s [after-fix]", evt, amt, why, _xp_key())
                    return
        else:
            why = kwargs.get("reason") or kwargs.get("tag") or kwargs.get("why") or ""
            log.info("[xp-bridge] %s +%s (%s) -> %s", evt, amt, why, _xp_key())

async def setup(bot):
    await bot.add_cog(XpEventBridgeOverlay(bot))