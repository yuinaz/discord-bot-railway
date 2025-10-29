from __future__ import annotations
import json, urllib.request
import logging, asyncio
from typing import Optional
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int, cfg_float, cfg_str
from satpambot.bot.modules.discord_bot.helpers import xp_award

log = logging.getLogger(__name__)

def _reasons() -> set[str]:
    s = cfg_str("PASSIVE_TO_BOT_REASONS", "passive_message,shadow_message,passive,shadow") or ""
    return {p.strip().lower() for p in s.replace(";",",").split(",") if p.strip()}

ENABLE = cfg_int("PASSIVE_TO_BOT_ENABLE", 1)
SHARE  = cfg_float("PASSIVE_TO_BOT_SHARE", 1.0)
LOCK_TTL = cfg_int("PASSIVE_TO_BOT_LOCK_TTL", 5)
LOCK_PREFIX = cfg_str("PASSIVE_TO_BOT_LOCK_PREFIX", "xp:lock:botbridge") or "xp:lock:botbridge"

def _hdr() -> Optional[str]:
    tok = cfg_str("UPSTASH_REDIS_REST_TOKEN", None)
    return f"Bearer {tok}" if tok else None

def _base() -> Optional[str]:
    return cfg_str("UPSTASH_REDIS_REST_URL", None)

async def _nx_lock(uid: int, reason: str) -> bool:
    base, auth = _base(), _hdr()
    if not base or not auth:
        # Without Upstash creds in module JSON, still allow (no lock)
        log.warning("[bot-bridge] Upstash creds missing in module JSON; awarding without NX lock")
        return True
    key = f"{LOCK_PREFIX}:{uid}:{reason}"
    payload = json.dumps([["SET", key, "1", "EX", str(int(LOCK_TTL)), "NX"]]).encode("utf-8")
    req = urllib.request.Request(f"{base}/pipeline", method="POST", data=payload)
    req.add_header("Authorization", auth); req.add_header("Content-Type", "application/json")
    loop = asyncio.get_running_loop()
    try:
        raw = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=3.5).read())
        return b"OK" in raw
    except Exception as e:
        log.debug("[bot-bridge] NX lock failed: %r", e)
        return False

class PassiveToBotBridgeOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _apply(self, uid: int, amount: int, reason: Optional[str]):
        if ENABLE != 1:
            return
        r = (reason or "").strip().lower()
        if r and _reasons() and (r not in _reasons()):
            return
        try:
            delta = int(amount)
        except Exception:
            return
        if delta <= 0:
            return
        if not await _nx_lock(uid, r or "passive"):
            return
        scaled = int(max(1, round(delta * SHARE)))
        loop = asyncio.get_running_loop()
        try:
            new_total, meta = await loop.run_in_executor(None, xp_award.award_xp_sync, scaled)
            log.info("[bot-bridge] +%s (from uid=%s reason=%s) -> total=%s", scaled, uid, r, new_total)
        except Exception as e:
            log.warning("[bot-bridge] award failed: %r", e)

    # Compatible listeners
    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        uid = kwargs.get("user_id") or kwargs.get("uid")
        amt = kwargs.get("amount")
        reason = kwargs.get("reason")
        if uid is None and len(args) >= 1: uid = args[0]
        if amt is None and len(args) >= 2: amt = args[1]
        if reason is None and len(args) >= 3: reason = args[2]
        if uid is not None and amt is not None:
            await self._apply(int(uid), int(amt), reason)

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        await self.on_xp_add(*args, **kwargs)

    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        await self.on_xp_add(*args, **kwargs)

async def setup(bot):
    await bot.add_cog(PassiveToBotBridgeOverlay(bot))

def setup(bot):  # sync fallback
    try:
        bot.add_cog(PassiveToBotBridgeOverlay(bot))
    except Exception:
        pass