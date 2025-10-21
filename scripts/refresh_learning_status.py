#!/usr/bin/env python3
"""
scripts/refresh_learning_status.py
- Reads data/neuro-lite/ladder.json (senior ladder costs, in order)
- Fetches xp:bot:senior_total from Upstash
- Computes label + percent + remaining
- Writes to:
    learning:status
    learning:status_json
Env:
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
"""
import os, sys, json, urllib.request, urllib.error
from pathlib import Path
from typing import Dict, Tuple

BASE = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
TOK  = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
LADDER_PATH = Path("data/neuro-lite/ladder.json")

def http_get(path: str) -> dict:
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        headers={"Authorization": f"Bearer {TOK}"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(path: str, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        data=data,
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def compute_label(total: int, senior_groups: Dict[str, Dict[str,int]]) -> Tuple[str, float, int]:
    # Iterate groups and levels in the order they appear in JSON
    running = int(total)
    for group_name, levels in senior_groups.items():
        for lvl_name, cost in levels.items():
            cost = int(cost)
            if running >= cost:
                running -= cost
            else:
                # inside this level
                done = cost - running
                percent = 100.0 * (cost - running) / cost
                # Wait, logic above reversed; fix:
                progress = cost - (cost - running) # actually progress so far in this level
                progress = int(cost - running)  # remaining? Let's compute cleanly below
                spent = int(total) - remaining_before_group_levels(senior_groups, group_name, lvl_name)
                # Simpler: remaining within this level is cost - running
                remaining = cost - running
                percent = (running / cost) * 100.0  # running here means leftover? No, we subtracted earlier.
                # Recompute correctly: before entering this level, we had 'running_before'
                # Start over with a clear computation:
                pass

def compute_from_scratch(total: int, senior_groups: Dict[str, Dict[str,int]]) -> Tuple[str, float, int]:
    running = int(total)
    for group_name, levels in senior_groups.items():
        for lvl_name, cost in levels.items():
            cost = int(cost)
            if running < cost:
                percent = (running / cost) * 100.0
                remaining = cost - running
                return f"{group_name}-{lvl_name}", round(percent, 1), remaining
            else:
                running -= cost
    # If exceed all levels
    last_group = list(senior_groups.keys())[-1]
    last_level = list(senior_groups[last_group].keys())[-1]
    return f"{last_group}-{last_level}", 100.0, 0

def main():
    if not BASE or not TOK:
        print("Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN", file=sys.stderr)
        sys.exit(2)
    if not LADDER_PATH.exists():
        print(f"Missing ladder file: {LADDER_PATH}", file=sys.stderr)
        sys.exit(2)

    ladder = json.loads(LADDER_PATH.read_text("utf-8"))
    senior = ladder.get("senior") or {}
    if not senior:
        print("ladder.json missing 'senior' section", file=sys.stderr)
        sys.exit(2)

    # 1) Get senior_total
    r = http_get("/get/xp:bot:senior_total")
    raw = r.get("result")
    try:
        total = int(raw)
    except Exception:
        try:
            obj = json.loads(raw)
            total = int(obj.get("senior_total_xp", 0))
        except Exception:
            total = 0

    label, pct, remaining = compute_from_scratch(total, senior)

    # 2) Write status
    status = f"{label} ({pct}%)"
    status_json = json.dumps({
        "label": label,
        "percent": float(pct),
        "remaining": int(remaining),
        "senior_total": int(total),
    }, separators=(",",":"))

    cmds = [
        ["SET","learning:status", status],
        ["SET","learning:status_json", status_json],
    ]
    out = http_post_json("/pipeline", cmds)
    print("Wrote:", out)
    print("Status:", status)
    print("JSON  :", status_json)

if __name__ == "__main__":
    main()
