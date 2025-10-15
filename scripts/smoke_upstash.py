#!/usr/bin/env python3
"""
Quick smoke to verify Upstash REST backend via our kv wrapper.
Usage:
  export KV_BACKEND=upstash_rest
  export UPSTASH_REDIS_REST_URL=...
  export UPSTASH_REDIS_REST_TOKEN=...
  python -m scripts.smoke_upstash
"""
import os, random
from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for
from satpambot.bot.modules.discord_bot.services.xp_store import XPStore

def main():
    url = os.getenv("UPSTASH_REDIS_REST_URL"); tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok:
        raise SystemExit("ENV UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN not set")

    # raw kv ping
    kv = get_kv_for("schedule")
    kv.set_json("ping:kv", {"ok": True})
    print("SET ping:kv ->", kv.get_json("ping:kv"))

    # xp test
    s = XPStore()
    g = 9999; u = random.randint(10000, 99999)
    print("add xp:", s.add_xp(g, u, 7))
    print("get xp:", s.get_user(g, u))

if __name__ == "__main__":
    main()
