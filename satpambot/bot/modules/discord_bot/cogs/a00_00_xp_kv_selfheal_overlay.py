from __future__ import annotations
import asyncio, logging, json, urllib.request, os
from typing import Optional
from discord.ext import commands, tasks
from satpambot.bot.modules.discord_bot.helpers.intish import parse_intish
log = logging.getLogger(__name__)
def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d
def _upstash_base() -> Optional[str]: return _env("UPSTASH_REDIS_REST_URL", None)
def _upstash_hdr() -> Optional[str]:
    tok = _env("UPSTASH_REDIS_REST_TOKEN", None); return f"Bearer {tok}" if tok else None
def _keys():
    main = _env("XP_TOTAL_KEY", "xp:bot:senior_total") or "xp:bot:senior_total"
    return [main, "xp:bot:senior_total_v2"]
async def _pipe(cmds):
    base, hdr = _upstash_base(), _upstash_hdr()
    if not base or not hdr: return None
    body = json.dumps(cmds).encode("utf-8")
    req = urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", hdr); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.5) as r:
        return json.loads(r.read().decode("utf-8","ignore"))
async def _get_raw(key: str) -> Optional[str]:
    try:
        r = await _pipe([["GET", key]]); return r and r[0].get("result")
    except Exception as e:
        log.debug("[xp-kv-selfheal] GET fail %s: %r", key, e); return None
async def _set_int(key: str, val: int) -> bool:
    try:
        _ = await _pipe([["SET", key, str(int(val))]]); return True
    except Exception as e:
        log.debug("[xp-kv-selfheal] SET fail %s: %r", key, e); return False
class XpKvSelfhealOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot; self.task.start()
    def cog_unload(self):
        try: self.task.cancel()
        except Exception: pass
    @tasks.loop(seconds=30)
    async def task(self):
        if not _upstash_base() or not _upstash_hdr(): return
        for k in _keys():
            raw = await _get_raw(k)
            ok, val = parse_intish(raw)
            if not ok or val is None: continue
            must_fix = False
            try:
                if str(int(raw)) != str(val): must_fix = True
            except Exception:
                must_fix = True
            if must_fix and await _set_int(k, val):
                log.warning("[xp-kv-selfheal] coerced %s -> %s", k, val)
    @task.before_loop
    async def _delay(self): import asyncio; await asyncio.sleep(8)
async def setup(bot): await bot.add_cog(XpKvSelfhealOverlay(bot))
def setup(bot):
    try: bot.add_cog(XpKvSelfhealOverlay(bot))
    except Exception: pass