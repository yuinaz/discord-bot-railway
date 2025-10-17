
"""
Ensure Upstash KV base keys exist so downstream bridge doesn't stop with 'KV missing; stop'.
Keys:
  - xp:store            (JSON with version/users/awards/stats/updated_at)
  - xp:bot:senior_total (int or {"senior_total_xp": int})
  - xp:ladder:TK        ({"L1": int, "L2": int})
"""
from __future__ import annotations
import os, logging, json, httpx, time

log = logging.getLogger(__name__)

URL = os.getenv("UPSTASH_REDIS_REST_URL")
TOK = os.getenv("UPSTASH_REDIS_REST_TOKEN")
HDR = {"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"} if TOK else {}

async def setup(bot):
    if not URL or not TOK:
        log.warning("[xp-kv-init] upstash env missing; skip")
        return

    async with httpx.AsyncClient(timeout=8.0) as x:
        async def cmd(*arr):
            r = await x.post(URL, headers=HDR, json=list(arr))
            r.raise_for_status()
            return r.json()

        # xp:store
        try:
            res = await cmd("GET", "xp:store")
            if not res.get("result"):
                now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                empty = {"version": 2, "users": {}, "awards": [], "stats": {"total": 0}, "updated_at": now}
                await cmd("SET", "xp:store", json.dumps(empty))
                log.info("[xp-kv-init] created xp:store")
        except Exception as e:
            log.warning("[xp-kv-init] xp:store check failed: %r", e)

        # xp:bot:senior_total
        try:
            res = await cmd("GET", "xp:bot:senior_total")
            if not res.get("result"):
                await cmd("SET", "xp:bot:senior_total", "0")
                log.info("[xp-kv-init] created xp:bot:senior_total=0")
        except Exception as e:
            log.warning("[xp-kv-init] senior_total check failed: %r", e)

        # xp:ladder:TK
        try:
            res = await cmd("GET", "xp:ladder:TK")
            if not res.get("result"):
                await cmd("SET", "xp:ladder:TK", json.dumps({"L1": 0, "L2": 500}))
                log.info("[xp-kv-init] created xp:ladder:TK")
        except Exception as e:
            log.warning("[xp-kv-init] ladder TK check failed: %r", e)
