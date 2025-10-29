
from __future__ import annotations
import logging, os, json, urllib.request, re
from typing import Optional, Any
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d

def _xp_key() -> str:
    return _env("XP_TOTAL_KEY","xp:bot:senior_total") or "xp:bot:senior_total"

def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok:
        return [{"error":"missing upstash env"}]
    out=[]
    for c in cmds:
        url = base.rstrip("/") + "/" + "/".join([c[0].lower()] + [str(x) for x in c[1:]])
        try:
            r = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
            with urllib.request.urlopen(r, timeout=15) as resp:
                try: out.append(json.loads(resp.read().decode()))
                except Exception as e: out.append({"result": None, "raw": str(e)})
        except Exception as e:
            out.append({"error": str(e)})
    return out

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
    except Exception: pass
    ints = re.findall(r"[-+]?\d+", str(raw))
    if ints:
        ints.sort(key=lambda s: (len(s.lstrip("+-")), int(s)), reverse=True)
        return int(ints[0])
    return 0

def _coerce_key_numeric(key: str) -> bool:
    r = _pipe([["GET", key]])
    raw = None
    try:
        raw = r[0].get("result")
    except Exception:
        pass
    if raw is None:
        ok = _pipe([["SET", key, "0"]])
        return not (ok and isinstance(ok,list) and "error" in ok[0])
    val = _smart_coerce(raw)
    ok = _pipe([["SET", key, str(val)]])
    return not (ok and isinstance(ok,list) and "error" in ok[0])

def _clamp(amt: int) -> int:
    try:
        a=int(amt)
        return 0 if a>10_000 or a<-10_000 else a
    except Exception:
        return 0

class XpEventBridgeOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener("on_xp_add")
    @commands.Cog.listener("on_xp.award")
    @commands.Cog.listener("on_satpam_xp")
    async def _on_xp(self, *args, **kwargs):
        evt = kwargs.get("event") or "xp_add"
        amt = kwargs.get("amount") or kwargs.get("delta") or kwargs.get("xp") or None
        if amt is None:
            for a in args:
                try:
                    amt=int(a); break
                except Exception: pass
        if not isinstance(amt, int) or amt == 0:
            log.debug("[xp-bridge] %s ignored amt=%r args=%r kwargs=%r", evt, amt, args, kwargs)
            return
        amt = _clamp(amt)
        r = _pipe([["INCRBY", _xp_key(), str(amt)]])
        if r and isinstance(r,list) and len(r)>0 and "error" in r[0]:
            log.warning("[xp-bridge] %s INCR err: %s (amt=%s) key=%s", evt, r[0]["error"], amt, _xp_key())
            if _coerce_key_numeric(_xp_key()):
                r2 = _pipe([["INCRBY", _xp_key(), str(amt)]])
                if r2 and isinstance(r2,list) and len(r2)>0 and "error" in r2[0]:
                    log.warning("[xp-bridge] retry failed: %s", r2[0]["error"])
                else:
                    why = kwargs.get("reason") or kwargs.get("tag") or kwargs.get("why") or ""
                    log.info("[xp-bridge] %s +%s (%s) -> %s [after-fix]", evt, amt, why, _xp_key())
                    return
            return
        else:
            why = kwargs.get("reason") or kwargs.get("tag") or kwargs.get("why") or ""
            log.info("[xp-bridge] %s +%s (%s) -> %s", evt, amt, why, _xp_key())

async def setup(bot):
    await bot.add_cog(XpEventBridgeOverlay(bot))
