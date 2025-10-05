# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from discord.ext import commands, tasks

try:
    from satpambot.ml import guard_hooks
except Exception:  # pragma: no cover
    guard_hooks = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


class SelfHealRuntime(commands.Cog):
    """Watchdog ringan: tidak restart proses, hanya soft-backoff saat error rate tinggi."""
    def __init__(self, bot: commands.Bot) -> None:  # type: ignore[name-defined]
        self.bot = bot
        self._task = self.watchdog.start()

    def cog_unload(self) -> None:
        try:
            self.watchdog.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=30.0)
    async def watchdog(self) -> None:
        if guard_hooks is None:
            return
        try:
            health: dict[str, Any] = guard_hooks.get_health()
            errors = int(health.get("errors", 0))
            last_at = float(health.get("last_error_at", 0.0))
            if errors >= 5 and (time.time() - last_at) < 300:
                # Soft backoff: beri jeda kecil agar pipeline tidak spiral error
                log.warning("[self-heal] high error rate: errors=%s; applying soft backoff", errors)
                await asyncio.sleep(2.0)
        except Exception as e:  # noqa: BLE001
            log.warning("[self-heal] watchdog error: %s", e)

    @watchdog.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot) -> None:  # type: ignore[name-defined]
    await bot.add_cog(SelfHealRuntime(bot))
