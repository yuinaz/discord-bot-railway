
import asyncio, json
from typing import Any, Dict, Optional
from discord.ext import commands

# Reuse helpers from xp_store_compat overlay
try:
    from .a06_xp_store_compat_overlay import load_store, save_store
except Exception:
    # Fallback local implementations (shouldn't happen if compat loaded)
    import os, datetime
    from pathlib import Path
    def _now_iso():
        return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    _STORE = {"version": 2, "users": {}, "awards": [], "stats": {"total": 0}, "updated_at": _now_iso()}
    def load_store(): return _STORE
    def save_store(d): _STORE.update(d)

def _norm_user_id(user) -> Optional[int]:
    try:
        if isinstance(user, int):
            return user
        if hasattr(user, "id"):
            return int(user.id)
        if isinstance(user, str) and user.isdigit():
            return int(user)
    except Exception:
        return None
    return None

def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

class XPAwardEventPersistOverlay(commands.Cog):
    """Listen to xp events and persist to store (file/Upstash)."""
    def __init__(self, bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    async def _apply_award(self, user_id: int, amount: int = 5, reason: str = "auto", meta: Optional[Dict[str, Any]] = None):
        async with self._lock:
            store = load_store()
            users = store.setdefault("users", {})
            stats = store.setdefault("stats", {"total": 0})
            u = users.setdefault(str(user_id), {"xp": 0, "updated_at": None})
            u["xp"] = _safe_int(u.get("xp", 0)) + _safe_int(amount, 0)
            u["updated_at"] = store["updated_at"]
            stats["total"] = _safe_int(stats.get("total", 0)) + _safe_int(amount, 0)
            # keep awards list small – only store last 50 lightweight entries
            awards = store.setdefault("awards", [])
            awards.append({"uid": user_id, "amt": amount, "r": reason})
            if len(awards) > 50:
                del awards[:-50]
            save_store(store)

    # Accept a few shapes:
    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        user = kwargs.get("user") or kwargs.get("author") or (args[0] if args else None)
        amount = kwargs.get("amount") or kwargs.get("xp") or (args[1] if len(args) > 1 else 5)
        reason = kwargs.get("reason") or "event:xp_add"
        uid = _norm_user_id(user)
        if uid:
            await self._apply_award(uid, _safe_int(amount, 5), reason)

    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        payload = kwargs.get("payload") or (args[0] if args else {})
        if isinstance(payload, dict):
            uid = _norm_user_id(payload.get("user") or payload.get("author") or payload.get("user_id"))
            amount = _safe_int(payload.get("amount") or payload.get("xp") or 5, 5)
            reason = payload.get("reason") or "event:xp_award"
            if uid:
                await self._apply_award(uid, amount, reason)

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        # very loose fallback
        uid = _norm_user_id(kwargs.get("user") or (args[0] if args else None))
        amount = _safe_int(kwargs.get("amount") or (args[1] if len(args) > 1 else 5), 5)
        reason = kwargs.get("reason") or "event:satpam_xp"
        if uid:
            await self._apply_award(uid, amount, reason)

async def setup(bot):
    await bot.add_cog(XPAwardEventPersistOverlay(bot))
    try:
        bot.logger.info("[xp_award_persist] ready – listening to xp_add/xp_award/satpam_xp")
    except Exception:
        print("[xp_award_persist] ready – listening to xp_add/xp_award/satpam_xp")
