
from __future__ import annotations
import logging, os
from typing import Any, Optional
from discord.ext import commands
from .helpers.upstash_rest import cmd as upstash_cmd, enabled as upstash_enabled

log = logging.getLogger(__name__)

def _norm_satpam_args(args: tuple, kwargs: dict) -> tuple[int, int, Optional[str]]:
    """
    Accept both styles:
      satpam_xp(uid, amount, reason)            # positional (preferred)
      satpam_xp(user_id=..., amount=..., reason=...)
      satpam_xp(user_id=..., delta=...,  reason=...)
    Return: (uid, amount, reason)
    """
    uid = None
    amount = None
    reason = None

    if args:
        # Try positional first
        if len(args) >= 2 and isinstance(args[0], int):
            uid = args[0]
            amount = args[1]
            if len(args) >= 3:
                reason = args[2]
    if uid is None:
        uid = kwargs.get("user_id") or kwargs.get("uid")
    if amount is None:
        amount = kwargs.get("amount", kwargs.get("delta"))
    if reason is None:
        reason = kwargs.get("reason")

    try:
        uid = int(uid) if uid is not None else None
    except Exception:
        uid = None
    try:
        amount = int(amount) if amount is not None else None
    except Exception:
        amount = None

    return uid, amount, reason

class XpUpstashSinkOverlay(commands.Cog):
    """
    Write exact-key XP to Upstash with robust event signature handling.
    ENV:
      XP_EXACT_KEY = xp:u:<uid>  (prefix, numeric suffix is uid)
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.exact_key_prefix = os.getenv("XP_EXACT_KEY_PREFIX", "xp:u:")

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args: Any, **kwargs: Any):
        if not upstash_enabled:
            return
        uid, amount, reason = _norm_satpam_args(args, kwargs)
        if uid is None or amount is None:
            log.warning("[xp-upstash-sink] dropped malformed satpam_xp event: args=%s kwargs=%s", args, kwargs)
            return
        try:
            # Store per-user exact key; allow negative too
            await upstash_cmd("INCRBY", f"{self.exact_key_prefix}{uid}", str(int(amount)))
            # Optional reasons bucket
            if reason:
                await upstash_cmd("HINCRBY", "xp:bucket:reasons", str(reason), str(int(amount)))
        except Exception as e:
            log.exception("[xp-upstash-sink] upstash write failed: %s", e)
