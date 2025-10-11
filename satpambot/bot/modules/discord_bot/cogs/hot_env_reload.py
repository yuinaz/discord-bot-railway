# hot_env_reload.py — safe async reload for discord.py variants
# - Watches SatpamBot.env and reloads all loaded extensions when file changes.
# - Uses reload_extensions_safely() helper to support both sync/async reload_extension API.
#
# Place at: satpambot/bot/modules/discord_bot/cogs/hot_env_reload.py

import os
import asyncio
import logging
from typing import List

from discord.ext import commands, tasks

# IMPORTANT: keep this import OUTSIDE any try/except block
from satpambot.bot.modules.discord_bot.helpers.hotenv_reload_helpers import reload_extensions_safely

log = logging.getLogger(__name__)


class HotEnvReload(commands.Cog):
    def __init__(self, bot: commands.Bot, env_path: str | None = None, interval_seconds: float = 2.0):
        self.bot = bot
        # Allow override via env var; default to SatpamBot.env in repo root
        self.env_path = env_path or os.environ.get("SATPAMBOT_ENV_FILE", "SatpamBot.env")
        self.interval_seconds = interval_seconds
        self._last_mtime: float | None = None
        # start watcher loop
        self._watch.start()

    def cog_unload(self):
        try:
            self._watch.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=2.0)
    async def _watch(self):
        """Poll the env file periodically and trigger reload on change."""
        # adjust interval dynamically if needed
        if self._watch.seconds != self.interval_seconds:
            self._watch.change_interval(seconds=self.interval_seconds)

        try:
            st = os.stat(self.env_path)
        except FileNotFoundError:
            if self._last_mtime is None:  # only warn once
                log.warning("[hotenv] env file not found: %s", self.env_path)
            await asyncio.sleep(0)
            return
        except Exception:
            log.exception("[hotenv] failed to stat env file: %s", self.env_path)
            return

        mtime = st.st_mtime
        if self._last_mtime is None:
            self._last_mtime = mtime
            return

        if mtime != self._last_mtime:
            self._last_mtime = mtime
            await self._on_change()

    @_watch.before_loop
    async def _before_loop(self):
        # Make sure the bot is ready
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    async def _on_change(self):
        log.info("[hotenv] detected change on %s; reloading all cogs...", self.env_path)

        # Collect currently loaded extensions
        try:
            exts: List[str] = list(self.bot.extensions.keys())
        except Exception:
            log.exception("[hotenv] unable to read bot extensions")
            return

        # Skip reloading this module's own extension name if present
        try:
            # Extension name resolution—depends on how you load this cog.
            # Usually it's "satpambot.bot.modules.discord_bot.cogs.hot_env_reload"
            this_ext = __name__
        except Exception:
            this_ext = None

        # Schedule safe reloads. This returns either an asyncio.Task (when in-loop)
        # or a concurrent.futures.Future (when called from thread); we don't need to await it.
        try:
            reload_extensions_safely(self.bot, exts, logger=log, skip_self=this_ext)
        except Exception:
            log.exception("[hotenv] scheduling reload failed")

        # Optional tiny delay to avoid flapping on rapid consecutive writes
        await asyncio.sleep(0.05)


async def setup(bot: commands.Bot):
    """discord.py async extension entry point"""
    await bot.add_cog(HotEnvReload(bot))
