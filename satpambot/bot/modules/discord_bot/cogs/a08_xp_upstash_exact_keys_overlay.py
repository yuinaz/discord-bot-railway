
from __future__ import annotations
import logging, os
from typing import Any, Optional
from discord.ext import commands

# Tolerant import: some trees don't export `enabled`
try:
    from ..helpers.upstash_rest import cmd as upstash_cmd  # async function
    _UPSTASH_OK = True
except Exception:  # pragma: no cover
    upstash_cmd = None
    _UPSTASH_OK = False

log = logging.getLogger(__name__)

def _norm_satpam_args(args: tuple, kwargs: dict) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Normalize satpam_xp event args coming from positional or kwargs emitters."""
    uid = None
    amount = None
    reason = None
    if args and len(args) >= 2 and isinstance(args[0], int):
        uid = args[0]
        amount = args[1]
        if len(args) >= 3:
            reason = args[2]
    if uid is None:
        u = kwargs.get("user_id") or kwargs.get("uid")
        if u is not None:
            try: uid = int(u)
            except Exception: uid = None
    if amount is None:
        a = kwargs.get("amount", kwargs.get("delta"))
        if a is not None:
            try: amount = int(a)
            except Exception: amount = None
    if reason is None:
        reason = kwargs.get("reason")
    return uid, amount, reason

class XpUpstashSinkOverlay(commands.Cog):
    """Write exact-key XP to Upstash; tolerant to mixed event signatures and import layouts."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.exact_key_prefix = os.getenv("XP_EXACT_KEY_PREFIX", "xp:u:")

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args: Any, **kwargs: Any):
        if not _UPSTASH_OK or upstash_cmd is None:
            # Upstash bridge not available; silently ignore
            return
        uid, amount, reason = _norm_satpam_args(args, kwargs)
        if uid is None or amount is None:
            log.warning("[xp-upstash-sink] drop malformed satpam_xp: args=%s kwargs=%s", args, kwargs)
            return
        try:
            await upstash_cmd("INCRBY", f"{self.exact_key_prefix}{uid}", str(int(amount)))
            if reason:
                await upstash_cmd("HINCRBY", "xp:bucket:reasons", str(reason), str(int(amount)))
        except Exception as e:  # pragma: no cover
            log.warning("[xp-upstash-sink] upstash write failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpUpstashSinkOverlay(bot))
