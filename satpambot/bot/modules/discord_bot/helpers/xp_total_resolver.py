
from __future__ import annotations
import os, json, logging, inspect, asyncio
from typing import Optional, Tuple
from pathlib import Path

log = logging.getLogger(__name__)

def _cfg_str(key: str, default: str) -> str:
    try:
        from satpambot.config.auto_defaults import cfg_str as _cs
        return _cs(key, default)
    except Exception:
        return os.getenv(key, default)

def _maybe_await(x):
    try:
        if inspect.isawaitable(x):
            return asyncio.get_running_loop().create_task(x)
    except Exception:
        pass
    return x

def _call_cmd(*args, **kwargs):
    try:
        from ..helpers.upstash_rest import cmd as upstash_cmd
    except Exception:
        # If helper is not available, return a dummy that yields None results
        def upstash_cmd(*a, **k):
            return {"result": None}
    res = upstash_cmd(*args, **kwargs)
    return res

def _parse_result(obj) -> Optional[str]:
    try:
        if isinstance(obj, dict):
            return obj.get("result")
        return obj
    except Exception:
        return None

async def resolve_senior_total() -> Optional[int]:
    """Prefer learning:status_json.senior_total, fallback to XP_SENIOR_KEY."""
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

def _ladder_path() -> Path:
    # Search upwards for data/ladder.json
    here = Path(__file__).resolve()
    for _ in range(8):
        cand = (here.parent / ("../" * _) / "data/ladder.json").resolve()
        if cand.exists():
            return cand
    return Path("data/ladder.json")

def load_kuliah_thresholds() -> list[tuple[str,int]]:
    """Return sorted list like [('S1', 0), ('S2', 19000), ...]."""
    try:
        p = _ladder_path()
        j = json.loads(p.read_text(encoding="utf-8"))
        import re
        items = []
        for k, v in j.get("KULIAH", {}).items():
            m = re.search(r"S(\d+)", k)
            if not m:
                continue
            items.append((int(m.group(1)), k, int(v)))
        items.sort()
        return [(k, v) for _, k, v in items]
    except Exception as e:
        log.warning("[xp-resolver] ladder load fail: %s; using static defaults", e)
        return [("S1", 0), ("S2", 19000), ("S3", 35000), ("S4", 58000),
                ("S5", 70000), ("S6", 96500), ("S7", 158000), ("S8", 220000), ("S8_CAP", 262500)]

def stage_from_total(total: int) -> tuple[str, float, dict]:
    th = load_kuliah_thresholds()
    cap = None
    for lab, val in th:
        if "CAP" in lab:
            cap = val
    if cap is None:
        cap = 10**12
    ordered = [(lab, val) for lab, val in th if "CAP" not in lab]
    current = ordered[0]
    for s in ordered:
        if total >= s[1]:
            current = s
        else:
            break
    idx = ordered.index(current)
    start = current[1]
    next_req = cap if idx == len(ordered) - 1 else ordered[idx + 1][1]
    width = max(1, next_req - start)
    pct = max(0.0, min(100.0, 100.0 * (total - start) / width))
    label = f"KULIAH-{current[0]}"
    meta = {"start_total": start, "required": next_req, "current": max(0, total - start)}
    return label, pct, meta
