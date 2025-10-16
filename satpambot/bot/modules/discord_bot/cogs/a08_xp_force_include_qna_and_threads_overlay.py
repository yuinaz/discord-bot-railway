
import os
import time
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

_QNA_ID = int(os.getenv("QNA_CHANNEL_ID", "1426571542627614772"))
# CSV of thread ids
_threads_csv = os.getenv("XP_PINNED_THREADS", "1372541073947361380,1371827576112152667,1389138326698852432,1389136684012015777")
_PINNED_THREADS = set()
for part in _threads_csv.split(","):
    part = part.strip()
    if part.isdigit():
        _PINNED_THREADS.add(int(part))

_FALLBACK_XP = int(os.getenv("FALLBACK_XP_PER_MSG", "5"))
_FALLBACK_COOLDOWN = int(os.getenv("FALLBACK_COOLDOWN_SECS", "45"))
_ALLOW_BOT_AWARD = os.getenv("XP_ALLOW_BOT_AWARD", "0") in ("1", "true", "True")

class XPForceIncludeOverlay(commands.Cog):
    """Guarantee XP scan runs in QNA channel and specified threads.
    If base XP system skips, we provide a minimal fallback award with cooldown.
    """
    def __init__(self, bot):
        self.bot = bot
        self._last_award = {}  # (user_id) -> ts

    def _should_award_here(self, message):
        ch_id = getattr(message.channel, "id", None)
        thr_id = getattr(message.channel, "id", None)
        return (ch_id == _QNA_ID) or (thr_id in _PINNED_THREADS)

    @commands.Cog.listener()
    async def on_message(self, message):
        # ignore DMs and system
        if not getattr(message, "guild", None):
            return
        # optionally ignore bot authors to avoid XP farming loops
        if message.author.bot and not _ALLOW_BOT_AWARD:
            return
        if not self._should_award_here(message):
            return

        # If base XP overlay already processed, nothing to do.
        # We can't reliably detect it, so we enforce a cooldown per user to be safe.
        uid = int(message.author.id)
        now = time.time()
        last = self._last_award.get(uid, 0)
        if now - last < _FALLBACK_COOLDOWN:
            return

        # Try route to XPStore if available
        try:
            from satpambot.bot.modules.discord_bot.services.xp_store import XPStore  # type: ignore
            store = XPStore.load()
            store.add_xp(uid, _FALLBACK_XP, reason="fallback:force-include-qna/threads")
            store.save()
            self._last_award[uid] = now
            log.debug("[xp_force] awarded %s XP to %s in %s", _FALLBACK_XP, uid, message.channel.id)
            return
        except Exception as e:
            log.warning("[xp_force] XPStore fallback failed: %r", e)

        # If XPStore missing, remain silent to avoid spam.
        self._last_award[uid] = now

async def setup(bot):
    await bot.add_cog(XPForceIncludeOverlay(bot))

def setup_legacy(bot):
    bot.add_cog(XPForceIncludeOverlay(bot))
