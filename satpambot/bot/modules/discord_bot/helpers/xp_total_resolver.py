
from __future__ import annotations
import os, json, logging, inspect, asyncio, re
from typing import Optional, Tuple, List
from pathlib import Path

log = logging.getLogger(__name__)

def _cfg_str(key: str, default: str) -> str:
    try:
        from satpambot.config.auto_defaults import cfg_str as _cs
        return _cs(key, default)
    except Exception:
        return os.getenv(key, default)

def _call_cmd(*args, **kwargs):
    try:
        from ..helpers.upstash_rest import cmd as upstash_cmd
    except Exception:
        def upstash_cmd(*a, **k):
            return {"result": None}
    return upstash_cmd(*args, **kwargs)

def _parse_result(obj) -> Optional[str]:
    try:
        if isinstance(obj, dict):
            return obj.get("result")
        return obj
    except Exception:
        return None

async def resolve_senior_total() -> Optional[int]:
    try:
        r = _call_cmd("GET", "learning:status_json")
        if inspect.isawaitable(r):
            r = await r
        s = _parse_result(r)
        if s:
            try:
                j = json.loads(s)
                v = j.get("senior_total")
                if v is not None:
                    return int(v)
            except Exception:
                pass
    except Exception as e:
        log.debug("[xp-resolver] status_json fail: %s", e)

    key = _cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")
    try:
        r = _call_cmd("GET", key)
        if inspect.isawaitable(r):
            r = await r
        s = _parse_result(r)
        if s is None:
            return None
        return int(s)
    except Exception as e:
        log.warning("[xp-resolver] read %s fail: %s", key, e)
        return None

_DEFAULTS = [("S1", 0), ("S2", 19000), ("S3", 35000), ("S4", 58000),
             ("S5", 70000), ("S6", 96500), ("S7", 158000), ("S8", 220000)]
_DEFAULT_CAP = 262500

def _ladder_path() -> Path:
    here = Path(__file__).resolve()
    for _ in range(10):
        cand = (here.parent / ("../" * _) / "data/ladder.json").resolve()
        if cand.exists():
            return cand
    return Path("data/ladder.json")

def _norm_pairs(pairs: List[tuple[str,int]]) -> List[tuple[str,int]]:
    items = []
    for k,v in pairs:
        m = re.search(r"S(\d+)", k, re.I)
        if not m:
            continue
        try:
            items.append((int(m.group(1)), f"S{m.group(1)}", int(v)))
        except Exception:
            continue
    items.sort()
    return [(lab, val) for _, lab, val in items]

def _ladder_from_dict(d: dict) -> List[tuple[str,int]]:
    src = None
    for kk in list(d.keys()):
        if kk.lower() == "kuliah":
            src = d[kk]
            break
    if src is None:
        src = d
    if isinstance(src, dict):
        return _norm_pairs([(k, src[k]) for k in src.keys()])
    return []

def _ladder_from_list(lst: list) -> List[tuple[str,int]]:
    pairs = []
    for it in lst:
        if isinstance(it, dict):
            lbl = it.get("label") or it.get("stage") or it.get("name")
            start = it.get("start_total", it.get("start"))
            if lbl is not None and start is not None:
                pairs.append((str(lbl), int(start)))
    return _norm_pairs(pairs)

def load_kuliah_thresholds() -> List[tuple[str,int]]:
    try:
        p = _ladder_path()
        j = json.loads(p.read_text(encoding="utf-8"))
        pairs: List[tuple[str,int]] = []
        if isinstance(j, dict):
            pairs = _ladder_from_dict(j)
        elif isinstance(j, list):
            pairs = _ladder_from_list(j)
        if not pairs:
            log.warning("[xp-resolver] ladder empty/invalid; using defaults")
            return _DEFAULTS.copy()
        return pairs
    except Exception as e:
        log.warning("[xp-resolver] ladder load fail: %s; using defaults", e)
        return _DEFAULTS.copy()

def stage_from_total(total: int) -> tuple[str, float, dict]:
    try:
        total = max(0, int(total))
    except Exception:
        total = 0

    ordered = load_kuliah_thresholds()
    if not ordered:
        ordered = _DEFAULTS.copy()

    cap = _DEFAULT_CAP
    if len(ordered) >= 2:
        last = ordered[-1][1]
        prev = ordered[-2][1]
        width = max(1000, last - prev)
        cap = last + width

    current_label, current_start = ordered[0]
    for lbl, start in ordered:
        if total >= start:
            current_label, current_start = lbl, start
        else:
            break

    idx = 0
    for i,(lbl, start) in enumerate(ordered):
        if lbl == current_label and start == current_start:
            idx = i; break
    next_req = cap if idx == len(ordered)-1 else ordered[idx+1][1]

    width = max(1, next_req - current_start)
    pct = max(0.0, min(100.0, 100.0 * (total - current_start) / width))
    label = f"KULIAH-{current_label}"
    meta = {"start_total": current_start, "required": next_req, "current": max(0, total-current_start)}
    return label, pct, meta
