
import logging
from typing import Any
from discord.ext import commands

from satpambot.bot.modules.discord_bot.services.xp_store_v2 import XPStoreV2

log = logging.getLogger(__name__)

def _extract_user_id(arg: Any):
    try:
        if hasattr(arg, "id"):
            return int(arg.id)
        return int(arg)
    except Exception:
        return None

class XPStoreBridge(commands.Cog):
    """
    Tangkap event XP dan persist ke XPStoreV2.
    Kompatibel: 'xp_add', 'xp.award', 'satpam_xp'.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = XPStoreV2()
        log.info("[xp-bridge] XPStoreBridge active (file=%s, upstash=%s)", self.store.store_path, getattr(self.store, "_upstash", None) and self.store._upstash.enabled)

    def _award(self, *args, **kwargs):
        user_id = None
        amount = int(kwargs.pop("amount", kwargs.pop("xp", 1)))
        reason = kwargs.pop("reason", None)
        award_key = kwargs.pop("award_key", kwargs.pop("message_id", None))

        if args:
            user_id = _extract_user_id(args[0])
        if user_id is None and "user_id" in kwargs:
            user_id = _extract_user_id(kwargs["user_id"])
        if user_id is None:
            log.warning("[xp-bridge] missing user_id in xp event (%s, %s)", args, kwargs)
            return

        ctx = {k: v for k, v in kwargs.items()
               if k not in ("amount", "xp", "reason", "award_key", "message_id", "user_id")}
        total = self.store.add_xp(user_id, amount=amount, reason=reason, context=ctx, award_key=award_key)
        log.info("[xp-bridge] +%s XP -> total=%s (user=%s, reason=%s)", amount, total, user_id, reason)

    # Listeners
    async def on_xp_add(self, *args, **kwargs):
        self._award(*args, **kwargs)

    async def on_xp_award(self, *args, **kwargs):
        self._award(*args, **kwargs)

    async def on_satpam_xp(self, *args, **kwargs):
        self._award(*args, **kwargs)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPStoreBridge(bot))
