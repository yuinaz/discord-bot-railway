from __future__ import annotations
import json, urllib.request, asyncio, logging, re
from typing import Optional
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_secret, cfg_str, cfg_int, cfg_float
from satpambot.bot.modules.discord_bot.helpers import xp_award

log = logging.getLogger(__name__)

def _tokens() -> list[str]:
    s = cfg_str("PASSIVE_TO_BOT_REASON_TOKENS", "passive,shadow,memory,normalize:chat,observer,passive-force-include") or ""
    return [t.strip().lower() for t in re.split(r"[\s,;]+", s) if t.strip()]

ENABLE   = int(cfg_str("PASSIVE_TO_BOT_ENABLE", "1") or "1")
SHARE    = cfg_float("PASSIVE_TO_BOT_SHARE", 1.0)
LOCK_TTL = cfg_int("PASSIVE_TO_BOT_LOCK_TTL", 5)
LOCK_PREFIX = cfg_str("PASSIVE_TO_BOT_LOCK_PREFIX", "xp:lock:botbridge") or "xp:lock:botbridge"

def _hdr() -> Optional[str]:
    tok = cfg_secret("UPSTASH_REDIS_REST_TOKEN", None)
    return f"Bearer {tok}" if tok else None

def _base() -> Optional[str]:
    return cfg_secret("UPSTASH_REDIS_REST_URL", None)

def _match_reason(reason: Optional[str]) -> bool:
    if not reason:
        return False
    r = reason.lower()
    for t in _tokens():
        if t in r:
            return True
    return False

async def _nx_lock(uid: int, reason: str) -> bool:
    base, auth = _base(), _hdr()
    if not base or not auth:
        log.warning("[passive→ladder] Upstash ENV missing; awarding WITHOUT NX lock")
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
        log.debug("[passive→ladder] NX lock failed: %r", e)
        return False

class PassiveShadowGlobalXPOverlay(commands.Cog):
    """
    Bridge PASTI (HYBRID): Semua XP bertag passive/shadow/memory/normalize:chat/observer
    -> naikkan xp:bot:senior_total (ladder Leina).
    - Secrets (Upstash URL/TOKEN) diambil dari ENV (menang atas JSON).
    - Parameter lain baca JSON overrides terlebih dulu.
    """
    def __init__(self, bot):
        self.bot = bot

    async def _apply(self, uid: int, amount: int, reason: Optional[str]):
        if ENABLE != 1:
            return
        if not _match_reason(reason):
            return
        try:
            delta = int(amount)
        except Exception:
            return
        if delta <= 0:
            return
        if not await _nx_lock(uid, (reason or "passive")):
            return
        scaled = int(max(1, round(delta * SHARE)))
        loop = asyncio.get_running_loop()
        try:
            new_total, meta = await loop.run_in_executor(None, xp_award.award_xp_sync, scaled)
            log.info("[passive→ladder] +%s (uid=%s reason=%s) -> total=%s", scaled, uid, reason, new_total)
        except Exception as e:
            log.warning("[passive→ladder] award failed: %r", e)

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
    async def on_satpam_xp(self, *a, **kw):
        await self.on_xp_add(*a, **kw)

    @commands.Cog.listener()
    async def on_xp_award(self, *a, **kw):
        await self.on_xp_add(*a, **kw)

async def setup(bot):
    await bot.add_cog(PassiveShadowGlobalXPOverlay(bot))

def setup(bot):  # sync fallback
    try:
        bot.add_cog(PassiveShadowGlobalXPOverlay(bot))
    except Exception:
        pass