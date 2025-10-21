#!/usr/bin/env python3
import os, json, urllib.request, urllib.error
from pathlib import Path

BASE = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
TOK  = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
LADDER_PATH = Path(os.getenv("LADDER_PATH","data/neuro-lite/ladder.json"))

def http_get(path: str) -> dict:
    req = urllib.request.Request(url=f"{BASE}{path}", headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(path: str, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{BASE}{path}", data=data, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def compute(total: int, senior: dict):
    running = int(total or 0)
    for g, levels in senior.items():
        for lvl, cost in levels.items():
            cost = int(cost)
            if running < cost:
                pct = round((running / cost) * 100.0, 1) if cost > 0 else 100.0
                return f"{g}-{lvl}", pct, (cost - running)
            running -= cost
    last_g = list(senior.keys())[-1]
    last_l = list(senior[last_g].keys())[-1]
    return f"{last_g}-{last_l}", 100.0, 0

def main():
    if not (BASE and TOK):
        print("Set UPSTASH_REDIS_REST_URL & UPSTASH_REDIS_REST_TOKEN"); return
    ladder = json.loads(LADDER_PATH.read_text("utf-8"))
    senior = ladder.get("senior") or {}
    raw = http_get("/get/xp:bot:senior_total").get("result")
    try:
        total = int(raw)
    except Exception:
        try: total = int(json.loads(raw).get("senior_total_xp",0))
        except Exception: total = 0
    label, pct, remaining = compute(total, senior)
    status = f"{label} ({pct}%)"
    status_json = json.dumps({"label":label,"percent":float(pct),"remaining":int(remaining),"senior_total":int(total)}, separators=(",",":"))
    out = http_post_json("/pipeline", [["SET","learning:status",status],["SET","learning:status_json",status_json]])
    print("Wrote:", out); print("Status:", status); print("JSON  :", status_json)

if __name__ == "__main__":
    main()
