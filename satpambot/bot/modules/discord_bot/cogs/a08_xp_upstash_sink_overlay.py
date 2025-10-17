
"""
XP Upstash Sink Overlay

- Listens to XP award events and keeps an Upstash key in sync:
    Key: xp:store  (single JSON blob with: version, users, awards, stats, updated_at)

- Also reads existing Upstash value on startup. If present and local store
  is empty/minimal, it nudges local snapshot writer (if available) via a
  gentle import hook (best-effort).

- Tolerant listeners that accept positional or keyword arguments.
"""
from __future__ import annotations
import os, json, time, asyncio, logging
from typing import Any, Dict, Optional

from discord.ext import commands

from .a06_upstash_client import discover_from_env

log = logging.getLogger(__name__)

UPSTASH_XP_STORE_KEY = "xp:store"

def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _safe_int(v: Any, d: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return d

def _coerce_store(store: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    # Ensure minimal shape to avoid KeyError('updated_at'), etc.
    if not isinstance(store, dict):
        store = {}
    store.setdefault("version", 2)
    store.setdefault("users", {})
    store.setdefault("awards", [])
    store.setdefault("stats", {"total": 0})
    store.setdefault("updated_at", _now_iso())
    # Coerce sub-structures
    if not isinstance(store["users"], dict):
        store["users"] = {}
    if not isinstance(store["awards"], list):
        store["awards"] = []
    if not isinstance(store["stats"], dict):
        store["stats"] = {"total": 0}
    store["stats"].setdefault("total", 0)
    return store

class XpUpstashSinkOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = discover_from_env()
        self._lock = asyncio.Lock()
        if self.redis and self.redis.ok():
            log.info("[xp-upstash] using Upstash at %s", os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("UPSTASH_URL"))
        else:
            log.warning("[xp-upstash] Upstash not configured; overlay will be idle.")

        # preload task
        self._preload_task = asyncio.create_task(self._preload_from_upstash()) if hasattr(self.bot, "loop") else asyncio.create_task(self._preload_from_upstash())

    async def _preload_from_upstash(self):
        # Best-effort: Pull xp:store and if it exists, advertise via log.
        if not (self.redis and self.redis.ok()):
            return
        try:
            store = await self.redis.get_json(UPSTASH_XP_STORE_KEY)
            if store:
                s = _coerce_store(store)
                total = s.get("stats", {}).get("total", 0)
                log.info("[xp-upstash] preload: users=%d total=%s updated_at=%s",
                         len(s.get("users", {})), total, s.get("updated_at"))
        except Exception as e:
            log.warning("[xp-upstash] preload failed: %r", e)

    # ---- Event helpers -----------------------------------------------------
    async def _apply_award(self, user_id: int, amount: int, reason: str = "") -> None:
        if not (self.redis and self.redis.ok()):
            return

        # prevent stampede
        async with self._lock:
            store = await self.redis.get_json(UPSTASH_XP_STORE_KEY)
            store = _coerce_store(store)

            uid = str(user_id)
            u = store["users"].setdefault(uid, {"xp": 0, "levels": {}, "history": []})
            u["xp"] = _safe_int(u.get("xp", 0), 0) + _safe_int(amount, 0)
            # keep compact history
            try:
                u_hist = u.setdefault("history", [])
                u_hist.append({"ts": int(time.time()), "delta": amount, "reason": reason or ""})
                if len(u_hist) > 50:
                    del u_hist[:-50]
            except Exception:
                u["history"] = [{"ts": int(time.time()), "delta": amount, "reason": reason or ""}]

            store["stats"]["total"] = _safe_int(store["stats"].get("total", 0), 0) + _safe_int(amount, 0)

            # push award event (tail 200 to keep size small)
            awards = store.setdefault("awards", [])
            awards.append({"uid": uid, "delta": amount, "reason": reason or "", "ts": int(time.time())})
            if len(awards) > 200:
                del awards[:-200]

            store["updated_at"] = _now_iso()
            ok = await self.redis.set_json(UPSTASH_XP_STORE_KEY, store)
            if not ok:
                log.warning("[xp-upstash] write failed")
            else:
                log.info("[xp-upstash] uid=%s %+d -> total=%d", uid, amount, u["xp"])

    def _parse_args(self, *args, **kwargs):
        user_id = None
        amount = None
        reason = ""

        # kwargs style
        if kwargs:
            user_id = kwargs.get("user_id") or kwargs.get("uid") or kwargs.get("member_id")
            amount = kwargs.get("amount") or kwargs.get("delta") or kwargs.get("xp")
            reason = kwargs.get("reason") or kwargs.get("why") or ""
        # positional style
        if user_id is None or amount is None:
            if len(args) >= 2:
                user_id, amount = args[0], args[1]
            if len(args) >= 3 and not reason:
                reason = args[2] or ""

        try:
            user_id = int(user_id) if user_id is not None else None
        except Exception:
            user_id = None
        try:
            amount = int(amount) if amount is not None else None
        except Exception:
            amount = None

        return user_id, amount, reason or ""

    # ---- Listeners ---------------------------------------------------------
    @commands.Cog.listener("on_xp_add")
    async def on_xp_add(self, *args, **kwargs):
        uid, amt, why = self._parse_args(*args, **kwargs)
        if uid is None or amt is None:
            log.debug("[xp-upstash] on_xp_add ignored (bad payload): args=%s kwargs=%s", args, kwargs)
            return
        await self._apply_award(uid, amt, why)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        uid, amt, why = self._parse_args(*args, **kwargs)
        if uid is None or amt is None:
            log.debug("[xp-upstash] on_satpam_xp ignored (bad payload): args=%s kwargs=%s", args, kwargs)
            return
        await self._apply_award(uid, amt, why)

    @commands.Cog.listener("on_xp_award")
    async def on_xp_award(self, *args, **kwargs):
        uid, amt, why = self._parse_args(*args, **kwargs)
        if uid is None or amt is None:
            log.debug("[xp-upstash] on_xp_award ignored (bad payload): args=%s kwargs=%s", args, kwargs)
            return
        await self._apply_award(uid, amt, why)


async def setup(bot):
    # Load as overlay cog
    try:
        await bot.add_cog(XpUpstashSinkOverlay(bot))
        log.info("[xp-upstash] overlay loaded")
    except Exception as e:
        log.warning("[xp-upstash] setup failed: %r", e)
