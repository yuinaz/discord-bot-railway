# -*- coding: utf-8 -*-
"""
XP Store (Upstash contract)
- xp:ladder:KULIAH => HGETALL -> {"result": ["S1","19000", "S2","35000", ...]}
- xp:ladder:MAGANG => HGETALL -> {"result": ["1TH","2000000"]}
- xp:bot:senior_total_v2 => GET -> {"result":"176957"}
- cfg:curriculum:pref => GET/SET -> "senior" / "magang" / "kerja" / "governor"
"""
from __future__ import annotations
import os, json, logging
from typing import Dict, Optional, Tuple, Any
import urllib.request, urllib.error

LOG = logging.getLogger(__name__)

def _u() -> str:
    u = (os.getenv("UPSTASH_REDIS_REST_URL") or "").strip()
    if not u: raise RuntimeError("UPSTASH_REDIS_REST_URL missing")
    return u.rstrip("/")

def _auth() -> str:
    t = (os.getenv("UPSTASH_REDIS_REST_TOKEN") or "").strip()
    if not t: raise RuntimeError("UPSTASH_REDIS_REST_TOKEN missing")
    return f"Bearer {t}"

def _req(path: str) -> Dict[str, Any]:
    url = f"{_u()}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={
        "Authorization": _auth(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8", "ignore")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        LOG.warning("[xp_store] http %s: %s", e.code, body[:200])
        raise
    except Exception as e:
        LOG.warning("[xp_store] request failed: %r", e)
        raise

def _parse_hgetall(resp: Dict[str, Any]) -> Dict[str, int]:
    arr = resp.get("result") or []
    if not isinstance(arr, list): return {}
    it = iter(arr)
    out: Dict[str, int] = {}
    for k in it:
        v = next(it, "0")
        try: out[str(k)] = int(str(v))
        except Exception:
            try: out[str(k)] = int(float(str(v)))
            except Exception: out[str(k)] = 0
    return out

class XpStore:
    def get_ladder_kuliah(self) -> Dict[str, int]:
        """Returns mapping S1..S8 -> int"""
        return _parse_hgetall(_req("hgetall/xp:ladder:KULIAH"))

    def get_ladder_magang(self) -> Dict[str, int]:
        """Returns mapping like {'1TH': 2000000}"""
        return _parse_hgetall(_req("hgetall/xp:ladder:MAGANG"))

    def get_senior_total(self) -> int:
        """xp:bot:senior_total_v2 -> int"""
        r = _req("get/xp:bot:senior_total_v2")
        try: return int(str(r.get("result") or "0"))
        except Exception:
            try: return int(float(str(r.get("result") or "0")))
            except Exception: return 0

    def get_curriculum_pref(self) -> Optional[str]:
        try:
            r = _req("get/cfg:curriculum:pref")
            val = (r.get("result") or "").strip().lower()
            return val or None
        except Exception:
            return None

    def set_curriculum_pref(self, value: str) -> bool:
        value = (value or "").strip().lower()
        if value not in ("senior","magang","kerja","governor"):
            raise ValueError("invalid pref value")
        r = _req(f"set/cfg:curriculum:pref/{value}")
        return str(r.get("result")).upper() == "OK"
