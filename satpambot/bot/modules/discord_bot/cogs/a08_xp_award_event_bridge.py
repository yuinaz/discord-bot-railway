# -*- coding: utf-8 -*-
"""
a08_xp_award_event_bridge.py
----------------------------
Provides a universal XP "shim" so producers can either call
- bot.xp_add(...)
- or dispatch events: "xp_add", "xp.award", "satpam_xp"
and this bridge will route them to XPStoreBridge cog (or any compatible cog).
Fixes: "No XP award shim found" warnings from history renderers.
"""
import asyncio
import inspect
import logging
from typing import Any, Dict
from discord.ext import commands

log = logging.getLogger(__name__)

class XPAwardEventBridge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Expose direct method for scanners that look for bot.xp_add
        if not hasattr(bot, "xp_add"):
            setattr(bot, "xp_add", self.xp_add)  # type: ignore[attr-defined]
            log.info("[xp-bridge] installed bot.xp_add shim")

    # -- Helpers ---------------------------------------------------------
    def _find_backend(self):
        # Prefer XPStoreBridge if present
        names = ["XPStoreBridge", "XpStoreBridge", "XPBridge", "XPDiscordBackend"]
        for n in names:
            cog = self.bot.get_cog(n)
            if cog is not None:
                return cog
        return None

    async def _call_dyn(self, func, *args, **kwargs):
        try:
            if inspect.iscoroutinefunction(func):
                sig = inspect.signature(func)
            else:
                sig = inspect.signature(func)
            # Keep only accepted kwargs
            ba = sig.bind_partial(*args, **{k: v for k, v in kwargs.items() if k in sig.parameters})
            ba.apply_defaults()
            res = func(*ba.args, **ba.kwargs)
            if inspect.isawaitable(res):
                return await res
            return res
        except Exception:
            log.exception("[xp-bridge] backend call failed")
            return None

    def _pick_method(self, backend):
        # Try common method names in order
        for name in ("xp_add", "award_xp", "award", "add_xp", "add", "give_xp", "give"):
            fn = getattr(backend, name, None)
            if callable(fn):
                return fn
        return None

    # -- Public API ------------------------------------------------------
    async def xp_add(self, user_id: int, amount: int, *, guild_id: int | None = None,
                     reason: str | None = None, message=None, channel_id: int | None = None, **extra) -> bool:
        backend = self._find_backend()
        if not backend:
            log.warning("[xp-bridge] no backend cog found for xp_add")
            return False
        fn = self._pick_method(backend)
        if not fn:
            log.warning("[xp-bridge] backend has no award method")
            return False
        # Try to pass rich context but keep it optional
        out = await self._call_dyn(fn,
            user_id=user_id, amount=amount, guild_id=guild_id,
            reason=reason, message=message, channel_id=channel_id, **extra
        )
        ok = bool(out is None or out is True or out == "OK")
        if ok:
            log.info("[xp-bridge] awarded +%s XP to %s via %s", amount, user_id, type(backend).__name__)
        return ok

    # -- Event listeners -------------------------------------------------
    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        try:
            if args and isinstance(args[0], int):
                user_id, amount = args[0], args[1]
                kwargs.setdefault("user_id", user_id)
                kwargs.setdefault("amount", amount)
            await self.xp_add(**kwargs)
        except Exception:
            log.exception("[xp-bridge] on_xp_add failed")

    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        await self.on_xp_add(*args, **kwargs)

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        await self.on_xp_add(*args, **kwargs)

async def setup(bot):
    await bot.add_cog(XPAwardEventBridge(bot))