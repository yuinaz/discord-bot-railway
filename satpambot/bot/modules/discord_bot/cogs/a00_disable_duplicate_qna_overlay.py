
from __future__ import annotations
import asyncio, logging
from discord.ext import commands

log = logging.getLogger(__name__)

AUTOREPLIES = [
    "a24_autolearn_qna_autoreply_fix_overlay",
    "a24_autolearn_qna_autoreply_patch",
    "a24_autolearn_qna_autoreply",
]

SCHEDULERS = [
    "a24_qna_autopilot_seed_overlay",
    "a24_qna_autopilot_scheduler",
    "a24_qna_autolearn_scheduler",
]

class DisableDuplicateQna(commands.Cog):
    """Keep exactly one QnA autoreply and one scheduler loaded.

    - Priority = order in lists above (earlier = preferred).
    - Re-enforced on_ready + on_cog_add + short scan loop (10s) to catch late loads.
    - Hardened: swallow all removal errors; never remove self.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._scan_task = bot.loop.create_task(self._short_scan())
        # Do a first pass quickly
        self._dedupe_all()

    async def cog_unload(self):
        try:
            self._scan_task.cancel()
        except Exception:
            pass

    async def _short_scan(self):
        # Re-apply dedupe a few times during boot to catch late-loaded cogs
        for _ in range(20):  # ~10s if 0.5s sleep
            try:
                self._dedupe_all()
            except Exception as e:
                log.debug("[qna-dup] scan error: %r", e)
            await asyncio.sleep(0.5)

    def _dedupe_group(self, priority_names, label="group"):
        try:
            present = [n for n in priority_names if n in self.bot.cogs and n != self.__class__.__name__]
            if len(present) <= 1:
                return
            keep = present[0]  # first in priority list
            for n in present[1:]:
                try:
                    # don't remove self if named similarly (safety)
                    if n == self.__class__.__name__:
                        continue
                    self.bot.remove_cog(n)
                    log.warning("[qna-dup] unloaded %s to avoid duplicate %s", n, label)
                except Exception:
                    # best-effort only
                    pass
            log.info("[qna-dup] keeping %s for %s", keep, label)
        except Exception as e:
            log.debug("[qna-dup] dedupe error: %r", e)

    def _dedupe_all(self):
        self._dedupe_group(AUTOREPLIES, "auto-answer")
        self._dedupe_group(SCHEDULERS, "scheduler")

    @commands.Cog.listener()
    async def on_ready(self):
        # One more pass when bot is fully ready
        self._dedupe_all()

    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        # Re-apply after a tick so the new cog name is in bot.cogs
        await asyncio.sleep(0.05)
        self._dedupe_all()

async def setup(bot: commands.Bot):
    # Robust async setup for d.py v2
    await bot.add_cog(DisableDuplicateQna(bot))

# Optional sync setup (older loaders); harmless if not used
def setup(bot: commands.Bot):
    try:
        bot.loop.create_task(bot.add_cog(DisableDuplicateQna(bot)))
    except Exception:
        # fallback: add immediately (older d.py)
        try:
            bot.add_cog(DisableDuplicateQna(bot))
        except Exception:
            pass
