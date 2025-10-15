#!/usr/bin/env python3
"""
Migrate local FileKV JSON -> Upstash REST (xp/schedule/dedup).
Usage:
  SATPAMBOT_CONFIG=<path-optional> \
  KV_BACKEND=upstash_rest \
  UPSTASH_REDIS_REST_URL=... \
  UPSTASH_REDIS_REST_TOKEN=... \
  python -m scripts.migrate_filekv_to_upstash

Optional env (if file paths differ from defaults):
  XP_FILE_PATH, SCHEDULE_FILE_PATH, DEDUP_FILE_PATH
"""
import os, json, sys
from pathlib import Path

from satpambot.bot.modules.discord_bot.utils.kv_backend import FileKV, UpstashREST

def load_filekv(path: str):
    p = Path(path)
    if not p.exists():
        print(f"[skip] file not found: {p}")
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception as e:
        print(f"[warn] failed to parse {p}: {e}")
        return {}

def main():
    url  = os.getenv("UPSTASH_REDIS_REST_URL")
    tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok:
        print("ERROR: set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN", file=sys.stderr)
        sys.exit(1)
    up = UpstashREST(url, tok)

    # default paths used by kv_backend.FileKV
    xp_path  = os.getenv("XP_FILE_PATH", "data/state/xp_store.kv.json")
    sch_path = os.getenv("SCHEDULE_FILE_PATH", "data/state/schedules.kv.json")
    ddp_path = os.getenv("DEDUP_FILE_PATH", "data/state/phish_dedup.kv.json")

    # migrate xp
    data = load_filekv(xp_path)
    if data:
        print(f"[migrate] xp: {len(data)} keys")
        for k, v in data.items():
            if k == "__ttl__": continue
            if not isinstance(v, dict): continue
            up.set_json(k, v)
        print("[done] xp")
    else:
        print("[skip] xp (no data)")

    # migrate schedule
    data = load_filekv(sch_path)
    if data:
        print(f"[migrate] schedule: {len(data)} keys")
        for k, v in data.items():
            if k == "__ttl__": continue
            if not isinstance(v, dict): continue
            up.set_json(k, v)
        print("[done] schedule")
    else:
        print("[skip] schedule (no data)")

    # migrate dedup (non-critical; optional)
    data = load_filekv(ddp_path)
    if data:
        print(f"[migrate] dedup: {len(data)} keys")
        for k, v in data.items():
            if k == "__ttl__": continue
            # store as simple marker; do not move TTLs (Upstash will set new TTL when seen again)
            up.set_json(k, {"migrated": True})
        print("[done] dedup")
    else:
        print("[skip] dedup (no data)")

if __name__ == "__main__":
    main()
