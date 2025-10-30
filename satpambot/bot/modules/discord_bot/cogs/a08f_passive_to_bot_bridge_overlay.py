
from __future__ import annotations
import logging, re
from typing import Optional
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers import xp_award
from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str, cfg_float

log = logging.getLogger(__name__)

def _coerce_ids(uid, amt):
    if hasattr(uid, "id"): uid = uid.id
    elif isinstance(uid, str):
        import re
        m = re.search(r"\d+", uid)
        if not m: raise TypeError(f"uid string invalid: {uid!r}")
        uid = int(m.group(0))
    else:
        uid = int(uid)
    if amt is None: amt = 0
    elif isinstance(amt, str):
        m = re.search(r"-?\d+", amt)
        if not m: raise TypeError(f"amt string invalid: {amt!r}")
        amt = int(m.group(0))
    else:
        amt = int(amt)
    return uid, amt

ENABLE = int(cfg_str("PASSIVE_BRIDGE_ENABLE", "1") or "1")
SHARE  = cfg_float("PASSIVE_BRIDGE_SHARE", 1.0)

class PassiveToBotBridgeOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _apply(self, user_id: int, amount: int, reason: Optional[str] = None):
        if not ENABLE or amount <= 0:
            return
        try:
            await xp_award.award(self.bot, int(user_id), int(amount), str(reason or "bridge"))
        except Exception as e:
            log.debug("[passive-bridge] apply failed: %r", e)

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        uid = kwargs.get("uid") if isinstance(kwargs, dict) else None
        amt = kwargs.get("amt") if isinstance(kwargs, dict) else None
        reason = kwargs.get("reason") if isinstance(kwargs, dict) else None
        if uid is None and len(args) >= 1: uid = args[0]
        if amt is None and len(args) >= 2: amt = args[1]
        if reason is None and len(args) >= 3: reason = args[2]
        if uid is None or amt is None:
            return
        try:
            _uid, _amt = _coerce_ids(uid, amt)
        except Exception as e:
            log.warning("[passive-bridge] bad payload uid=%r amt=%r reason=%r err=%r", uid, amt, reason, e)
            return
        await self._apply(_uid, _amt, reason)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        await self.on_xp_add(*args, **kwargs)

async def setup(bot):
    await bot.add_cog(PassiveToBotBridgeOverlay(bot))
