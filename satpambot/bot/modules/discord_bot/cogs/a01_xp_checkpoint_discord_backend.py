
import os
import re
import asyncio
import logging
from importlib import import_module
from discord.ext import commands

from satpambot.bot.utils.xp_state_discord import DiscordState

BONUS_TK = int(os.getenv("XP_RESET_BONUS_TK", "1000"))
BONUS_SD = int(os.getenv("XP_RESET_BONUS_SD", "1000"))
BONUS_DEFAULT = int(os.getenv("XP_RESET_BONUS_DEFAULT", "0"))

RE_XP = re.compile(r"\[passive-learning\]\s*\+(\d+)\s*XP\s*->\s*total=(\d+)\s*level=([A-Za-z0-9_-]+)")
LOGGERS_TO_TAP = [
    "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer",
    "modules.discord_bot.cogs.learning_passive_observer",
]
log = logging.getLogger(__name__)

def _db_dsn_present() -> bool:
    return bool(os.getenv("RENDER_POSTGRES_URL") or os.getenv("DATABASE_URL"))

def _resolve_learning_module():
    for name in [
        __name__.split(".cogs.")[0] + ".cogs.learning_passive_observer",
        "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer",
        "modules.discord_bot.cogs.learning_passive_observer",
    ]:
        try:
            return import_module(name)
        except Exception:
            continue
    return None

class _RegexFilter(logging.Filter):
    def __init__(self, pattern: re.Pattern[str]): super().__init__(); self.p = pattern
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            return bool(self.p.search(record.getMessage() or ""))
        except Exception:
            return False

class XPDiscordBackend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state = DiscordState()
        self._handler = None
        self._last_total = None
        self._last_seen_total = None
        self._reset_floor = None
        self._installed = False

    @commands.Cog.listener()
    async def on_ready(self):
        if _db_dsn_present():
            log.info("[xp/discord] DB present; skipping discord backend")
            return
        try:
            total, level = await self.state.load(self.bot)
            if total is not None:
                await self._apply_restore(total, level)
                self._last_total = total
                log.info("[xp/discord] restored total=%s level=%s from pinned message", total, level)
            # phase-2 restore after late init
            async def later():
                await asyncio.sleep(5)
                t,l = await self.state.load(self.bot)
                if t is not None:
                    await self._apply_restore(t,l)
                    self._last_total = max(self._last_total or 0, t)
            asyncio.create_task(later())
        except Exception:
            log.exception("[xp/discord] restore failed")

        if not self._installed:
            self._installed = True
            self._handler = self._make_handler()
            self._handler.addFilter(_RegexFilter(RE_XP))
            # Attach to both specific and root to be safe
            for name in LOGGERS_TO_TAP:
                logging.getLogger(name).addHandler(self._handler)
            logging.getLogger().addHandler(self._handler)  # root

    async def _apply_restore(self, total: int, level: str):
        lpo = _resolve_learning_module()
        if not lpo:
            log.warning("[xp/discord] learning_passive_observer not available; skip in-process restore")
            return
        try:
            if hasattr(lpo, "set_total_from_checkpoint"):
                maybe = lpo.set_total_from_checkpoint(total, level)
                if asyncio.iscoroutine(maybe):
                    await maybe
                return
            cur = getattr(lpo, "TOTAL_XP", 0)
            if isinstance(cur, (int, float)) and total > cur:
                setattr(lpo, "TOTAL_XP", int(total))
                setattr(lpo, "LEVEL", level or getattr(lpo, "LEVEL", "TK"))
        except Exception:
            log.exception("[xp/discord] apply restore failed")

    def _make_handler(self):
        backend = self
        class _H(logging.Handler):
            def emit(inner, record):
                msg = record.getMessage()
                m = RE_XP.search(msg)
                if not m:
                    return
                try:
                    total = int(m.group(2))
                    level = m.group(3)

                    if backend._last_seen_total == total:
                        return
                    backend._last_seen_total = total

                    prev = backend._last_total

                    # if we already detected reset and set a floor, ignore lower totals
                    if backend._reset_floor is not None and total < backend._reset_floor:
                        try:
                            asyncio.get_running_loop().create_task(
                                backend.state.save(backend.bot, backend._reset_floor, level)
                            )
                        except RuntimeError:
                            pass
                        return

                    if prev is not None and total < prev:
                        bonus = BONUS_TK if level.upper() == "TK" else BONUS_SD if level.upper() == "SD" else BONUS_DEFAULT
                        corrected = max(prev, total) + bonus
                        backend._last_total = corrected
                        backend._reset_floor = corrected
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(backend.state.save(backend.bot, corrected, level))
                            loop.create_task(backend._apply_restore(corrected, level))
                        except RuntimeError:
                            pass
                        log.warning("[xp/discord] RESET detected prev=%s now=%s -> +%s => %s", prev, total, bonus, corrected)
                        return

                    backend._last_total = total
                    if backend._reset_floor is not None and total >= backend._reset_floor:
                        backend._reset_floor = None
                    try:
                        asyncio.get_running_loop().create_task(backend.state.save(backend.bot, total, level))
                    except RuntimeError:
                        pass
                except Exception:
                    log.exception("[xp/discord] tap failed")
        h = _H()
        h.setLevel(logging.INFO)
        return h

async def setup(bot):
    res = await bot.add_cog(XPDiscordBackend(bot))
    import asyncio as _aio
    if _aio.iscoroutine(res):
        await res