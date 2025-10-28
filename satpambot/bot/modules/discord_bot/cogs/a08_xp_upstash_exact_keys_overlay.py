
from __future__ import annotations
import os, logging, inspect, asyncio
from typing import Any, Optional
from discord.ext import commands
from ..helpers.upstash_rest import cmd as upstash_cmd

log = logging.getLogger(__name__)

def _norm(args: tuple, kwargs: dict) -> tuple[Optional[int], Optional[int], Optional[str]]:
    uid = None; amount = None; reason = None
    if args and len(args) >= 2 and isinstance(args[0], int):
        uid, amount = args[0], args[1]
        if len(args) >= 3:
            reason = args[2]
    if uid is None:
        u = kwargs.get("user_id") or kwargs.get("uid")
        try: uid = int(u) if u is not None else None
        except Exception: uid = None
    if amount is None:
        a = kwargs.get("amount", kwargs.get("delta"))
        try: amount = int(a) if a is not None else None
        except Exception: amount = None
    if reason is None:
        reason = kwargs.get("reason")
    return uid, amount, reason

def _maybe_await(x):
    try:
        if inspect.isawaitable(x):
            return asyncio.get_running_loop().create_task(x)
    except Exception:
        pass
    return x

class XpUpstashSinkOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.prefix = os.getenv("XP_EXACT_KEY_PREFIX", "xp:u:")

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args: Any, **kwargs: Any):
        uid, amount, reason = _norm(args, kwargs)
        if uid is None or amount is None:
            log.warning("[xp-upstash-sink] drop malformed satpam_xp: args=%s kwargs=%s", args, kwargs)
            return
        try:
            _maybe_await(upstash_cmd("INCRBY", f"{self.prefix}{uid}", str(int(amount))))
            if reason:
                _maybe_await(upstash_cmd("HINCRBY", "xp:bucket:reasons", str(reason), str(int(amount))))
        except Exception as e:
            log.warning("[xp-upstash-sink] upstash write failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpUpstashSinkOverlay(bot))
