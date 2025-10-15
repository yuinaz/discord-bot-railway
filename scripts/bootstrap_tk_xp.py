#!/usr/bin/env python3
import os, json, datetime
from pathlib import Path

TK_FILE = Path("data/learn/tk_xp.json")
DEFAULT_KEY = "xp:bot:tk_total"

def _load():
    if TK_FILE.exists():
        try:
            import json
            return json.loads(TK_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tk_total_xp": 0, "levels": {}, "last_update": None}

def _save(obj):
    TK_FILE.parent.mkdir(parents=True, exist_ok=True)
    TK_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def maybe_upstash_store(obj):
    if os.getenv("KV_BACKEND") != "upstash_rest":
        return False, "KV_BACKEND!=upstash_rest"
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    key = os.getenv("TK_XP_KEY", DEFAULT_KEY)
    if not url or not token:
        return False, "Missing Upstash URL/TOKEN"
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    try:
        try:
            import requests
            r = requests.post(url.rstrip("/") + "/set/" + key, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}, timeout=10)
            ok = r.status_code == 200 and "OK" in r.text.upper()
            return ok, f"HTTP {r.status_code} {r.text[:120]}"
        except Exception:
            import urllib.request
            req = urllib.request.Request(url.rstrip("/") + "/set/" + key, data=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                txt = resp.read().decode("utf-8","ignore")
                ok = "OK" in txt.upper()
                return ok, txt[:120]
    except Exception as e:
        return False, repr(e)

def main():
    xp1 = int(os.getenv("XP1", "1000"))
    xp2 = int(os.getenv("XP2", "500"))
    obj = _load()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    obj["tk_total_xp"] = int(obj.get("tk_total_xp", 0)) + xp1 + xp2
    lv = obj.setdefault("levels", {})
    lv["L1"] = int(lv.get("L1", 0)) + xp1
    lv["L2"] = int(lv.get("L2", 0)) + xp2
    obj["last_update"] = now
    _save(obj)
    print(f"[OK] TK total xp={obj['tk_total_xp']} (L1+=%d, L2+=%d)" % (xp1, xp2))
    ok, msg = maybe_upstash_store(obj)
    print("[Upstash]", "OK" if ok else "SKIP", msg)

if __name__ == "__main__":
    main()