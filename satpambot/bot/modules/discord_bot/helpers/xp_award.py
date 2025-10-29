from __future__ import annotations
import json, urllib.request
from typing import Dict, Any, Tuple

from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_from_total

def _hdr() -> Dict[str,str]:
    tok = cfg_str("UPSTASH_REDIS_REST_TOKEN", None)
    return {"Authorization": f"Bearer {tok}"} if tok else {}

def _base() -> str|None:
    return cfg_str("UPSTASH_REDIS_REST_URL", None)

def _total_key() -> str:
    return cfg_str("XP_TOTAL_KEY", "xp:bot:senior_total") or "xp:bot:senior_total"

def award_xp_sync(delta: int) -> Tuple[int, Dict[str, Any]]:
    base = _base()
    hdr = _hdr()
    if not base or not hdr:
        raise RuntimeError("Upstash config missing in module JSON (UPSTASH_REDIS_REST_URL/_TOKEN)")
    # INCRBY + GET
    pipeline = [["INCRBY", _total_key(), str(int(delta))],
                ["GET", _total_key()]]
    req = urllib.request.Request(f"{base}/pipeline", method="POST",
                                 data=json.dumps(pipeline).encode("utf-8"))
    req.add_header("Content-Type","application/json")
    for k,v in hdr.items(): req.add_header(k,v)
    with urllib.request.urlopen(req, timeout=4.0) as r:
        resp = json.loads(r.read().decode("utf-8","ignore"))
    new_total = int(resp[1]["result"])

    # compute ladder & refresh status keys
    label, pct, meta = stage_from_total(new_total)
    rem = max(0, int(meta.get("required",0)) - int(meta.get("current",0)))
    status_json = json.dumps({"label":label,"percent":pct,"remaining":rem,"senior_total":new_total,"stage":meta}, separators=(",",":"))
    pipeline2 = [["SET","learning:status",f"{label} ({pct}%)"],
                 ["SET","learning:status_json",status_json]]
    req2 = urllib.request.Request(f"{base}/pipeline", method="POST",
                                  data=json.dumps(pipeline2).encode("utf-8"))
    req2.add_header("Content-Type","application/json")
    for k,v in hdr.items(): req2.add_header(k,v)
    with urllib.request.urlopen(req2, timeout=4.0) as r2:
        _ = r2.read()
    return new_total, meta