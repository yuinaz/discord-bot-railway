
import asyncio
import gc
import logging
import os
import sys
import typing
import ctypes

try:
    import discord
    from discord.ext import commands
except Exception as e:
    # Let import error propagate with clear message
    raise

log = logging.getLogger(__name__)

def _rss_mb() -> float:
    """Return current process RSS in MB without external deps."""
    # Try /proc/self/statm (Linux)
    try:
        with open("/proc/self/statm", "r") as f:
            parts = f.readline().split()
            if len(parts) >= 2:
                rss_pages = int(parts[1])
                page_size = os.sysconf("SC_PAGE_SIZE")
                return (rss_pages * page_size) / (1024 * 1024)
    except Exception:
        pass

    # Try resource (may be Kb on Linux, bytes on others)
    try:
        import resource  # type: ignore
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Heuristic: Linux returns KiB, macOS returns bytes
        if rss > 10 * 1024 * 1024:  # looks like bytes
            return rss / (1024 * 1024)
        else:  # assume KiB
            return rss / 1024
    except Exception:
        pass

    # Fallback: unknown, return 0
    return 0.0

def _malloc_trim() -> None:
    """Attempt to return freed heap to OS (glibc only)."""
    try:
        libc = ctypes.CDLL("libc.so.6")  # Linux/glibc
        libc.malloc_trim(0)
    except Exception:
        # Ignore on non-glibc systems
        pass

class MemoryGuard(commands.Cog):
    """
    Lightweight guard to reduce OOM restarts.
    Runs a small loop that checks RSS and triggers GC/malloc_trim
    when crossing thresholds.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interval_sec = int(os.getenv("MEM_GUARD_INTERVAL_SEC", "12"))
        self.soft_mb = int(os.getenv("MEM_GUARD_SOFT_MB", "420"))
        self.hard_mb = int(os.getenv("MEM_GUARD_HARD_MB", "480"))
        self._task: typing.Optional[asyncio.Task] = None
        self._last_level = "init"

    async def _free_mem(self, level: str) -> None:
        # Only log when level changes to avoid spam
        if level != self._last_level:
            log.warning("[memory-guard] pressure=%s rss=%.1fMB (soft=%s hard=%s) -> GC",
                        level, _rss_mb(), self.soft_mb, self.hard_mb)
            self._last_level = level
        gc.collect()
        _malloc_trim()

    async def _runner(self) -> None:
        await self.bot.wait_until_ready()
        log.info("[memory-guard] started (interval=%ss soft=%sMB hard=%sMB)",
                 self.interval_sec, self.soft_mb, self.hard_mb)
        try:
            while not self.bot.is_closed():
                rss = _rss_mb()
                if rss >= self.hard_mb:
                    await self._free_mem("HARD")
                elif rss >= self.soft_mb:
                    await self._free_mem("SOFT")
                await asyncio.sleep(self.interval_sec)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("[memory-guard] loop crashed")
        finally:
            log.info("[memory-guard] stopped")

    @commands.Cog.listener()
    async def on_ready(self):
        # Ensure the runner is started once
        if self._task is None or self._task.done():
            self._task = self.bot.loop.create_task(self._runner())

    def cog_unload(self):
        if self._task and not self._task.done():
            self._task.cancel()

# discord.py 2.x uses async setup; keep legacy fallback for loaders
async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryGuard(bot))

# Some custom loaders still call sync setup; keep it available
def setup_legacy(bot: commands.Bot):  # pragma: no cover
    bot.add_cog(MemoryGuard(bot))
