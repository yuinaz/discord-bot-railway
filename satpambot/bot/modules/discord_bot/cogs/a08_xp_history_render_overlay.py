from discord.ext import commands
from discord.ext import tasks

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict, Set

import discord
from discord.ext import commands, tasks

LOG = logging.getLogger(__name__)

# -------- tunables for Render free --------
QNA_CHANNEL_IDS = {1426571542627614772}
SINCE_DAYS = 2
AWARD_PER_MESSAGE = 5
MAX_MESSAGES = 400
MAX_PER_USER = 150
SLEEP_MS = 420
AUTHOR_COOLDOWN_SEC = 15
CHANNEL_COOLDOWN_SEC = 6
# -----------------------------------------

def _now() -> float:
    return time.time()

class _Cooldown:
    def __init__(self, sec: float):
        self.sec = sec
        self.last = 0.0
    async def wait(self):
        dt = _now() - self.last
        if dt < self.sec:
            await asyncio.sleep(self.sec - dt)
        self.last = _now()

class XPHistoryRenderOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._seen_msg: Set[int] = set()
        self._per_user: Dict[int, int] = defaultdict(int)
        self._author_cool = defaultdict(lambda: _Cooldown(AUTHOR_COOLDOWN_SEC))
        self._chan_cool = defaultdict(lambda: _Cooldown(CHANNEL_COOLDOWN_SEC))
        self._task = self.scan_loop.start()

    def cog_unload(self):
        try:
            self.scan_loop.cancel()
        except Exception:
            pass

    @tasks.loop(minutes=15.0)
    async def scan_loop(self):
        # wait ready
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass
        await self.scan_once()

    @scan_loop.before_loop
    async def _before(self):
        await asyncio.sleep(5)

    async def _iter_target_channels(self):
        for gid, guild in list(self.bot.guilds_by_id.items()) if hasattr(self.bot, "guilds_by_id") else []:
            # Not all bots maintain map; fallback to bot.get_channel
            pass
        for ch_id in QNA_CHANNEL_IDS:
            ch = self.bot.get_channel(ch_id)
            if isinstance(ch, (discord.TextChannel, discord.Thread)):
                yield ch

    async def scan_once(self):
        import datetime as _dt
        total = 0
        cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=SINCE_DAYS)
        for ch in [c async for c in self._iter_target_channels()]:
            try:
                await self._chan_cool[ch.id].wait()
                async for msg in ch.history(limit=MAX_MESSAGES, after=cutoff, oldest_first=True):
                    if msg.id in self._seen_msg:
                        continue
                    self._seen_msg.add(msg.id)
                    if msg.author.bot:
                        # reward bot self-learning interactions too (QnA transcripts)
                        pass
                    await self._author_cool[msg.author.id].wait()
                    if self._per_user[msg.author.id] >= MAX_PER_USER:
                        continue
                    try:
                        await self._award_xp(msg, AWARD_PER_MESSAGE)
                        self._per_user[msg.author.id] += AWARD_PER_MESSAGE
                        total += AWARD_PER_MESSAGE
                        await asyncio.sleep(SLEEP_MS/1000.0)
                    except Exception as e:
                        LOG.warning("[xp-render] award skipped: %r", e)
            except Exception as e:
                LOG.warning("[xp-render] scan channel %s failed: %r", getattr(ch, "id", "?"), e)
        if total:
            LOG.info("[xp-render] awarded %s XP (scan)", total)

    async def _award_xp(self, msg: discord.Message, amount: int):
        # Call into existing XP overlay if present; otherwise no-op
        # Try v2 direct method shim that repo already exposes
        try:
            from satpambot.bot.modules.discord_bot.cogs.a08_xp_direct_method_shim import award_xp_direct
            await award_xp_direct(self.bot, msg.author.id, amount, reason="render:history")
            return
        except Exception:
            pass
        # Try older message-awarder overlay
        try:
            from satpambot.bot.modules.discord_bot.cogs.a08_xp_message_awarder_overlay import award_xp_for_message
            await award_xp_for_message(msg, base=amount)
            return
        except Exception:
            pass
        raise RuntimeError("No XP award shim found")

async def setup(bot):
    await bot.add_cog(XPHistoryRenderOverlay(bot))


# --- PATCH: award fallback via event ---
try:

    class _XPHistoryAwardFallback(_cmds.Cog):
        def __init__(self, bot):
            self.bot = bot
        async def _award_event(self, msg, amount: int, reason: str = "history"):
            try:
                self.bot.dispatch("xp_add",
                    user_id=getattr(msg.author, "id", None),
                    amount=int(amount),
                    guild_id=getattr(getattr(msg, "guild", None), "id", None),
                    channel_id=getattr(getattr(msg, "channel", None), "id", None),
                    message_id=getattr(msg, "id", None),
                    reason=reason
                )
                return True
            except Exception:
                return False
    async def setup(bot):
        try:
            await bot.add_cog(_XPHistoryAwardFallback(bot))
        except Exception:
            pass
except Exception:
    pass