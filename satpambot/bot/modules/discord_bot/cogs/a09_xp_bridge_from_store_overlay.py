# a09_xp_bridge_from_store_overlay.py
# Read-only mirror from xp:store (STRING JSON schema v2) -> update ladder & totals in Upstash.
# DOES NOT modify xp:store. Does not touch a08_xp_upstash_exact_keys_overlay or configs.
# Safe to remove anytime; it only writes: xpbridge:last_total_xp, xp:ladder:*, xp:bot:*_total, xp:bot:senior_total

import os, json, asyncio, logging
from discord.ext import commands

try:
    import httpx  # used as fallback if kv.incrby is not available
except Exception:
    httpx = None

log = logging.getLogger(__name__)

PHASE_KEYS = {
    "TK":       ("xp:ladder:TK",       "xp:bot:tk_total",       "L1"),
    "SMP":      ("xp:ladder:SMP",      "xp:bot:smp_total",      "L1"),
    "SMA":      ("xp:ladder:SMA",      "xp:bot:sma_total",      "L1"),
    "KULIAH":   ("xp:ladder:KULIAH",   "xp:bot:kuliah_total",   "S1"),
}

class XpBridgeFromStore(commands.Cog):

    async def _incr_senior_total_safely(self, delta: int):
        key = "xp:bot:senior_total"
        raw = await self._kv_get(key)
        if raw is None:
            await self._kv_set(key, "0")
            raw = "0"
        try:
            int(raw)
            await self._kv_incrby(key, delta)
            return
        except Exception:
            pass
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "senior_total_xp" in obj:
                cur = int(obj.get("senior_total_xp") or 0)
                obj["senior_total_xp"] = cur + int(delta)
                await self._kv_set(key, json.dumps(obj, separators=(",",":")))
                return
        except Exception:
            pass
        mirror = "xp:bot:senior_total_xp"
        if await self._kv_get(mirror) is None:
            await self._kv_set(mirror, "0")
        await self._kv_incrby(mirror, delta)
    """Bridge XP from xp:store into ladder/totals.
       - READS: xp:store (STRING JSON schema v2)
       - WRITES: xpbridge:last_total_xp, xp:ladder:* (JSON), xp:bot:*_total (int), xp:bot:senior_total (int)
       - NEVER touches xp:store, nor a08 overlay/configs."""

    def __init__(self, bot):
        self.bot = bot
        self.kv  = getattr(bot, "kv", None)
        self.interval = 10  # seconds
        self._task = asyncio.create_task(self._loop())

    async def cog_unload(self):
        t = getattr(self, "_task", None)
        if t: t.cancel()

    async def _kv_get(self, key: str):
        if not self.kv:
            return None
        try:
            return await self.kv.get(key)
        except Exception:
            log.warning("[xpbridge] kv.get(%s) failed", key, exc_info=True)
            return None

    async def _kv_set(self, key: str, val: str):
        if not self.kv:
            return
        try:
            return await self.kv.set(key, val)
        except Exception:
            log.warning("[xpbridge] kv.set(%s) failed", key, exc_info=True)

    async def _kv_incrby(self, key: str, delta: int):
        # Prefer kv.incrby if available
        if self.kv and hasattr(self.kv, "incrby") and callable(getattr(self.kv, "incrby")):
            try:
                return await self.kv.incrby(key, delta)
            except Exception:
                log.warning("[xpbridge] kv.incrby(%s,%s) failed; trying REST fallback", key, delta, exc_info=True)

        # Fallback: direct Upstash REST call (no dependency on provider having incrby)
        url  = os.environ.get("UPSTASH_REDIS_REST_URL")
        tok  = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not url or not tok or httpx is None:
            # last resort: approximate by read+set (non-atomic) -- try to avoid, but better than nothing
            try:
                cur = await self._kv_get(key)
                cur_i = int(cur or 0)
                new_i = cur_i + int(delta)
                await self._kv_set(key, str(new_i))
                return {"result": str(new_i)}
            except Exception:
                log.warning("[xpbridge] non-atomic set fallback failed for %s", key, exc_info=True)
                return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as x:
                r = await x.post(url, headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"},
                                 json=["INCRBY", key, str(delta)])
                r.raise_for_status()
                return r.json()
        except Exception:
            log.warning("[xpbridge] REST INCRBY failed for %s", key, exc_info=True)
            return None

    async def _loop(self):
        await self.bot.wait_until_ready()
        if not self.kv:
            log.warning("[xpbridge] KV missing; stop")
            return

        STORE = "xp:store"
        WATERMARK = "xpbridge:last_total_xp"

        while not self.bot.is_closed():
            try:
                raw = await self._kv_get(STORE)   # READ-ONLY
                if raw:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        log.warning("[xpbridge] xp:store bad JSON", exc_info=True)
                        data = None

                    if isinstance(data, dict):
                        users = data.get("users") or {}
                        new_total_xp = 0
                        for u in users.values():
                            try:
                                new_total_xp += int(u.get("xp", 0))
                            except Exception:
                                pass

                        last_total = 0
                        lt = await self._kv_get(WATERMARK)
                        try:
                            last_total = int(lt or 0)
                        except Exception:
                            last_total = 0

                        if new_total_xp > last_total:
                            delta = new_total_xp - last_total

                            # 1) senior_total mirrors overall delta
                            await self._kv_incrby("xp:bot:senior_total", delta)

                            # 2) phase-based ladder & total
                            phase = (await self._kv_get("learning:phase")) or "TK"
                            ladder_key, bot_total_key, first_level = PHASE_KEYS.get(phase, PHASE_KEYS["TK"])

                            # update ladder JSON (increment field)
                            try:
                                ladder_raw = await self._kv_get(ladder_key)
                                ladder = json.loads(ladder_raw) if ladder_raw else {}
                                if not isinstance(ladder, dict):
                                    ladder = {}
                                cur = int(ladder.get(first_level, 0))
                                ladder[first_level] = cur + delta
                                await self._kv_set(ladder_key, json.dumps(ladder, separators=(',',':')))
                            except Exception:
                                log.warning("[xpbridge] ladder update fail (%s)", ladder_key, exc_info=True)

                            # 3) update bot total (ignore if key not used in layout)
                            if bot_total_key:
                                try:
                                    await self._kv_incrby(bot_total_key, delta)
                                except Exception:
                                    pass

                            await self._kv_set(WATERMARK, str(new_total_xp))
                            log.info("[xpbridge] %+d | phase=%s -> ladder(%s.%s)+%d, senior_total+%d",
                                     delta, phase, ladder_key, first_level, delta, delta)
                # else: xp:store missing/empty — do nothing
            except asyncio.CancelledError:
                break
            except Exception:
                log.warning("[xpbridge] loop error", exc_info=True)

            await asyncio.sleep(self.interval)


async def setup(bot):
    await bot.add_cog(XpBridgeFromStore(bot))
