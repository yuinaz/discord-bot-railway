# -*- coding: utf-8 -*-
"""XP Consistency Overlay (Upstash auto-heal) — v2 (same as v1, safe import)
- Runs once on_ready to unify totals (MAX of v1/v2 keys), recompute label,
  and write learning:status & learning:status_json atomically.
- No side effects on import; respects on_ready bootstrap rule.
"""
from __future__ import annotations
import os, json, asyncio, logging
from typing import Any, List, Tuple
try:
    import discord  # noqa: F401
    from discord.ext import commands  # type: ignore
except Exception:
    commands = object  # type: ignore

import urllib.request, urllib.error

log = logging.getLogger(__name__)

def _upstash_base():
    b = (os.getenv("UPSTASH_REDIS_REST_URL","") or "").rstrip("/")
    return b or None

def _upstash_auth():
    t = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
    return t or None

def _pipeline(cmds: List[List[str]]) -> tuple[int, Any]:
    base = _upstash_base(); tok = _upstash_auth()
    if not base or not tok:
        return (0, "UPSTASH env missing")
    req = urllib.request.Request(f"{base}/pipeline",
        data=json.dumps(cmds).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            try:
                return (r.getcode(), json.loads(body))
            except Exception:
                return (r.getcode(), body)
    except urllib.error.HTTPError as e:
        try: body = e.read().decode()
        except Exception: body = str(e)
        return (e.code, body)
    except Exception as e:
        return (-1, str(e))

S_NAMES = ("S1","S2","S3","S4","S5","S6","S7","S8")
S_TH = (19000, 35000, 58000, 70000, 96500, 158000, 220000, 262500)

def _to_int(x)->int:
    try:
        return int(float(str(x).strip()))
    except Exception:
        return 0

def _calc(total:int):
    idx=0
    for i,th in enumerate(S_TH):
        if total>=th: idx=i
    cur=S_TH[idx]; nxt=S_TH[idx] if idx==len(S_TH)-1 else S_TH[idx+1]
    if nxt<=cur:
        pct=100.0; rem=0
    else:
        pct=round(max(0.0,(total-cur)/float(nxt-cur)*100.0),1)
        rem=max(0,nxt-total)
    label=f"KULIAH-{S_NAMES[idx]}"
    status=f"{label} ({pct}%)"
    j={"label":label,"percent":pct,"remaining":rem,"senior_total":total}
    return label,status,j

async def _heal():
    base=_upstash_base(); tok=_upstash_auth()
    if not base or not tok:
        log.warning("[xp-autoheal] UPSTASH env missing"); return
    keyA = os.getenv("XP_SENIOR_KEY") or os.getenv("SENIOR_XP_KEY") or "xp:bot:senior_total"
    keyB=None
    code,res = _pipeline([["GET",keyA],["GET","learning:status"],["GET","learning:status_json"]])
    if code<=0: log.warning("[xp-autoheal] read failed: %s",res); return
    try:
        A=_to_int(res[0].get("result")); B=_to_int(res[1].get("result"))
        status_raw = res[2].get("result") or ""
        json_raw = res[3].get("result") or "{}"
    except Exception:
        A=B=0; status_raw=""; json_raw="{}"
    total=max(A,B)
    label,status,j=_calc(total)
    need=True
    try:
        lbl_s = (status_raw.split(" ",1)[0] if status_raw else "")
        import json as _j; lbl_j = _j.loads(json_raw).get("label","")
        need = (A!=B) or (lbl_s!=label) or (lbl_j!=label)
    except Exception: need=True
    if not need:
        log.info("[xp-autoheal] consistent: %s",label); return
    import json as _j
    cmds=[["SET",keyA,str(total)],
          ["SET","learning:status",status],
          ["SET","learning:status_json", _j.dumps(j,separators=(',',':'))]]
    code2,res2=_pipeline(cmds)
    if 200<=code2<300: log.info("[xp-autoheal] fixed -> %s (total=%s)",label,total)
    else: log.warning("[xp-autoheal] write failed: %s %s",code2,res2)

class XPConsistencyOverlay(commands.Cog if commands!=object else object):
    def __init__(self, bot=None): self.bot=bot; self._task=None
    @getattr(commands,"Cog",object).listener()
    async def on_ready(self):
        if os.getenv("XP_DISABLE_AUTOHEAL"): 
            log.info("[xp-autoheal] disabled"); return
        if self._task is None:
            self._task = asyncio.create_task(self._once())
    async def _once(self):
        await asyncio.sleep(2.0)
        try: await _heal()
        except Exception as e: log.exception("[xp-autoheal] error: %s",e)

def setup(bot):
    try:
        bot.add_cog(XPConsistencyOverlay(bot))
        log.info("✅ Loaded cog: %s", __name__)
    except Exception as e:
        log.exception("Failed to load XPConsistencyOverlay: %s", e)


async def setup(bot):
    try:
        await bot.add_cog(XPConsistencyOverlay(bot))
        log.info('✅ Loaded cog (async): %s', __name__)
    except Exception as e:
        log.exception('Failed to load XPConsistencyOverlay (async): %s', e)
