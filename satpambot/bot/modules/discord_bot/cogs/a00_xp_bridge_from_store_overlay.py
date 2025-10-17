# a00_xp_bridge_from_store_overlay.py (v4 SAFE)
# Works with DummyBot (no .loop / no wait_until_ready). No config changes required.
# READ-ONLY from xp:store (schema v2) -> updates ladder & totals mirrors.
# Does NOT touch xp:store.

import os, json, asyncio, logging
from discord.ext import commands, tasks

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

PHASE_KEYS = {
    "TK":       ("xp:ladder:TK",       "xp:bot:tk_total",       "L1"),
    "SMP":      ("xp:ladder:SMP",      "xp:bot:smp_total",      "L1"),
    "SMA":      ("xp:ladder:SMA",      "xp:bot:sma_total",      "L1"),
    "KULIAH":   ("xp:ladder:KULIAH",   "xp:bot:kuliah_total",   "S1"),
}

STORE_KEY = "xp:store"
WATERMARK = "xpbridge:last_total_xp"

class XpBridgeFromStoreSAFE(commands.Cog):
    """Bridge: mirror deltas from xp:store -> ladder/totals (no touch xp:store)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.kv  = getattr(bot, "kv", None)
        # Do NOT access bot.loop; do NOT schedule task here.
        log.info("[xpbridge] SAFE init (no loop access)")

    @property
    def qualified_name(self) -> str:
        return "XpBridgeFromStoreSAFE"

    # ---- KV helpers ----
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
            return None
        try:
            return await self.kv.set(key, val)
        except Exception:
            log.warning("[xpbridge] kv.set(%s) failed", key, exc_info=True)
            return None

    async def _kv_incrby_atomic(self, key: str, delta: int):
        if self.kv and hasattr(self.kv, "incrby"):
            try:
                return await self.kv.incrby(key, delta)
            except Exception:
                log.warning("[xpbridge] kv.incrby(%s,%s) failed; REST fallback", key, delta, exc_info=True)

        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if url and tok and httpx is not None:
            try:
                async with httpx.AsyncClient(timeout=10.0) as x:
                    r = await x.post(url, headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"},
                                     json=["INCRBY", key, str(delta)])
                    r.raise_for_status()
                    return r.json()
            except Exception:
                log.warning("[xpbridge] REST INCRBY failed for %s", key, exc_info=True)

        # last resort non-atomic
        try:
            cur = await self._kv_get(key)
            cur_i = int(cur or 0)
            new_i = cur_i + int(delta)
            await self._kv_set(key, str(new_i))
            return {"result": str(new_i)}
        except Exception:
            log.warning("[xpbridge] non-atomic set fallback failed for %s", key, exc_info=True)
            return None

    async def _incr_senior_total_safely(self, delta: int):
        key = "xp:bot:senior_total"
        raw = await self._kv_get(key)
        if raw is None:
            await self._kv_set(key, "0")
            raw = "0"
        # integer?
        try:
            int(raw)
            await self._kv_incrby_atomic(key, delta)
            return
        except Exception:
            pass
        # JSON?
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "senior_total_xp" in obj:
                cur = int(obj.get("senior_total_xp") or 0)
                obj["senior_total_xp"] = cur + int(delta)
                await self._kv_set(key, json.dumps(obj, separators=(',',':')))
                return
        except Exception:
            pass
        # fallback mirror
        mirror = "xp:bot:senior_total_xp"
        if await self._kv_get(mirror) is None:
            await self._kv_set(mirror, "0")
        await self._kv_incrby_atomic(mirror, delta)

    async def _incr_phase_total_if_present(self, bot_total_key: str, delta: int):
        if not bot_total_key:
            return
        raw = await self._kv_get(bot_total_key)
        if raw is None:
            return
        try:
            int(raw)
        except Exception:
            return
        await self._kv_incrby_atomic(bot_total_key, delta)

    def _sum_users_total(self, data: dict) -> int:
        users = data.get("users") or {}
        return sum(int(u.get("xp", 0)) for u in users.values() if isinstance(u, dict))

    @tasks.loop(seconds=8.0)
    async def runner(self):
        # This loop doesn't assume bot.wait_until_ready / bot.loop
        if not self.kv:
            # stop silently in DummyBot smoke
            return
        raw = await self._kv_get(STORE_KEY)
        if not raw:
            return
        try:
            data = json.loads(raw)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        new_total = self._sum_users_total(data)
        lt = await self._kv_get(WATERMARK)
        try:
            last = int(lt or 0)
        except Exception:
            last = 0
        if new_total > last:
            delta = new_total - last
            await self._incr_senior_total_safely(delta)
            phase = (await self._kv_get("learning:phase")) or "TK"
            ladder_key, bot_total_key, first_level = PHASE_KEYS.get(phase, PHASE_KEYS["TK"])
            # ladder
            ladder_raw = await self._kv_get(ladder_key)
            try:
                ladder = json.loads(ladder_raw) if ladder_raw else {}
                if not isinstance(ladder, dict):
                    ladder = {}
            except Exception:
                ladder = {}
            cur = int(ladder.get(first_level, 0))
            ladder[first_level] = cur + delta
            await self._kv_set(ladder_key, json.dumps(ladder, separators=(',',':')))
            # phase total (optional)
            await self._incr_phase_total_if_present(bot_total_key, delta)
            # watermark
            await self._kv_set(WATERMARK, str(new_total))
            log.info("[xpbridge] %+d | phase=%s -> ladder(%s.%s)+%d; senior_total += %d",
                     delta, phase, ladder_key, first_level, delta, delta)

    async def cog_load(self):
        # start loop safely; if event loop not running (smoke), tasks.loop will start when possible
        if self.runner.is_running():
            self.runner.cancel()
        try:
            self.runner.start()
        except RuntimeError:
            # In rare sync-smoke contexts, event loop not running yet; schedule a delayed start
            async def _delayed():
                await asyncio.sleep(0.1)
                if not self.runner.is_running():
                    try: self.runner.start()
                    except Exception: pass
            asyncio.create_task(_delayed())

    async def cog_unload(self):
        if self.runner.is_running():
            self.runner.cancel()

async def setup(bot: commands.Bot):
    # just add; do not touch other cogs / configs
    await bot.add_cog(XpBridgeFromStoreSAFE(bot))
    log.info("[xpbridge] a00_xp_bridge_from_store_overlay (v4 SAFE) loaded")
