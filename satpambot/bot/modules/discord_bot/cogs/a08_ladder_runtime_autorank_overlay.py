# a08_ladder_runtime_autorank_overlay.py
from __future__ import annotations
import os, json, asyncio, logging
from typing import Dict, Any, List, Tuple, Optional
import discord
from discord.ext import commands, tasks
log = logging.getLogger(__name__)
def _env(*names, default=""):
    for n in names:
        v = os.getenv(n)
        if v and str(v).strip():
            return str(v).strip()
    return default
def _upstash():
    base = _env("UPSTASH_REST_URL","UPSTASH_REDIS_REST_URL").rstrip("/")
    tok  = _env("UPSTASH_REST_TOKEN","UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return "", {}
    return base, {"Authorization": f"Bearer {tok}", "Content-Type":"application/json"}
async def _http_json(session, method, url, *, headers, json_body=None):
    import aiohttp
    async with session.request(method, url, headers=headers, json=json_body) as resp:
        try: return await resp.json()
        except Exception: return {"status": resp.status, "text": await resp.text()}
async def _get_xp(session) -> Optional[int]:
    base, hdr = _upstash()
    if not base: return None
    key = _env("XP_SENIOR_KEY", default="xp:bot:senior_total")
    data = await _http_json(session, "POST", f"{base}/pipeline", headers=hdr, json_body=[["GET", key]])
    try: return int(data[0]["result"]) if data and data[0]["result"] is not None else None
    except Exception: return None
def _load_json(cands: List[str]) -> Optional[Dict[str,Any]]:
    for p in cands:
        try:
            with open(p,"r",encoding="utf-8") as f: return json.load(f)
        except Exception: continue
    try:
        import importlib.resources as ir
        with ir.files("satpambot.bot.data").joinpath("ladder.json").open("r",encoding="utf-8") as f:
            return json.load(f)
    except Exception: return None
def _kuliah_quotas()->List[int]:
    d=_load_json(["data/neuro-lite/ladder.json","satpambot/bot/data/ladder.json"]) or {}
    k=d.get("KULIAH") or d.get("kuliah") or {}
    keys=["S1","S2","S3","S4","S5","S6","S7","S8"]
    vals=[int(k.get(x)) for x in keys if k.get(x) is not None]
    if len(vals)>=8: return vals[:8]
    return [19000,35000,58000,70000,96500,158000,220000,262500]
def _magang_quota()->int:
    d=_load_json(["data/neuro-lite/ladder.json","satpambot/bot/data/ladder.json"]) or {}
    m=d.get("MAGANG") or d.get("magang") or {}
    return int(m.get("1TH", 2000000))
def _work_overall()->List[int]:
    d=_load_json(["data/config/xp_work_ladder.json"]) or {}
    o=d.get("overall") or {}
    vals=[int(o.get(k)) for k in ["L1","L2","L3","L4"] if o.get(k) is not None]
    return vals or [5000000,7000000,9000000,12000000]
def _phase(total:int,kq:List[int],mq:int,wq:List[int])->Tuple[str,int,int,int]:
    cum=0
    for i,q in enumerate(kq,1):
        if total<cum+q:
            return "KULIAH",i,cum,q
        cum+=q
    if total<cum+mq:
        return "MAGANG",1,cum,mq
    cum2=cum+mq
    for i,q in enumerate(wq,1):
        if total<cum2+q:
            return "WORK",i,cum2,q
        cum2+=q
    return "GOVERNOR",1,cum2,1
def _label(phase:str,idx:int)->str:
    return ("KULIAH-S"+str(idx)) if phase=="KULIAH" else ("MAGANG-S1" if phase=="MAGANG" else ("WORK-L"+str(idx) if phase=="WORK" else "GOVERNOR"))
async def _write(session,label,percent,remaining,xp,start_total,required):
    base,hdr=_upstash()
    if not base: return
    payload=[
        ["SET","learning:status",f"{label} ({percent:.1f}%)"],
        ["SET","learning:status_json",json.dumps({"label":label,"percent":round(percent,1),"remaining":remaining,"senior_total":xp,"stage":{"start_total":start_total,"required":required,"current":xp-start_total}})]
    ]
    await _http_json(session,"POST",f"{base}/pipeline",headers=hdr,json_body=payload)
class AutoRank(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot=bot
        self._last=""
        sec=max(10,int(_env("LADDER_REFRESH_SECS",default="60") or "60"))
        self.loop.change_interval(seconds=sec)
        self.loop.start()
    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass
    @tasks.loop(seconds=60.0)
    async def loop(self):
        import aiohttp
        async with aiohttp.ClientSession() as s:
            xp=await _get_xp(s)
            if xp is None: return
            kq=_kuliah_quotas(); mq=_magang_quota(); wq=_work_overall()
            phase,idx,start,req=_phase(xp,kq,mq,wq)
            cur=max(0,xp-start); rem=max(0,req-cur); pct=100.0 if req<=0 else min(100.0,(cur/req)*100.0)
            lab=_label(phase,idx)
            js={"label":lab,"percent":round(pct,1),"remaining":rem,"senior_total":xp,"stage":{"start_total":start,"required":req,"current":cur}}
            key=str(js)
            if key!=self._last:
                await _write(s,lab,pct,rem,xp,start,req)
                self._last=key
                log.warning("[autorank] %s (%.1f%%) xp=%s", lab, pct, xp)
    @loop.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5.0)
async def setup(bot:commands.Bot):
    await bot.add_cog(AutoRank(bot))
