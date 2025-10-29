from __future__ import annotations
import json, urllib.request
from typing import Dict, Any, Tuple

from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_secret, cfg_str
from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_from_total

def _hdr() -> Dict[str,str]:
    tok = cfg_secret("UPSTASH_REDIS_REST_TOKEN", None)
    if not tok:
        raise RuntimeError("UPSTASH_REDIS_REST_TOKEN missing (ENV)")
    return {"Authorization": f"Bearer {tok}"}

def _base() -> str:
    base = cfg_secret("UPSTASH_REDIS_REST_URL", None)
    if not base:
        raise RuntimeError("UPSTASH_REDIS_REST_URL missing (ENV)")
    return base

def _total_key() -> str:
    return cfg_str("XP_TOTAL_KEY", "xp:bot:senior_total") or "xp:bot:senior_total"

def award_xp_sync(delta: int) -> Tuple[int, Dict[str, Any]]:
    base = _base()
    hdr = _hdr()

    pipeline = [["INCRBY", _total_key(), str(int(delta))],
                ["GET", _total_key()]]
    req = urllib.request.Request(f"{base}/pipeline", method="POST",
                                 data=json.dumps(pipeline).encode("utf-8"))
    req.add_header("Content-Type","application/json")
    for k,v in hdr.items(): req.add_header(k,v)
    with urllib.request.urlopen(req, timeout=4.0) as r:
        resp = json.loads(r.read().decode("utf-8","ignore"))
    new_total = int(resp[1]["result"])

    label, pct, meta = stage_from_total(new_total)
    remaining = max(0, int(meta.get("required",0)) - int(meta.get("current",0)))
    status_json = json.dumps({"label":label,"percent":pct,"remaining":remaining,"senior_total":new_total,"stage":meta}, separators=(",",":"))
    pipe2 = [["SET","learning:status",f"{label} ({pct}%)"],
             ["SET","learning:status_json",status_json]]
    req2 = urllib.request.Request(f"{base}/pipeline", method="POST",
                                  data=json.dumps(pipe2).encode("utf-8"))
    req2.add_header("Content-Type","application/json")
    for k,v in hdr.items(): req2.add_header(k,v)
    with urllib.request.urlopen(req2, timeout=4.0) as r2:
        _ = r2.read()

    return new_total, meta