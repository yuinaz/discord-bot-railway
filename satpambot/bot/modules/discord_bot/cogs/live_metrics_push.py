# Push live metrics to dashboard store every N seconds.
from __future__ import annotations

import os
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import tasks, commands

try:
    import psutil
except Exception:
    psutil = None

# Defaults; override via ENV
GUILD_ID_DEFAULT = int(os.environ.get("SATPAMBOT_METRICS_GUILD_ID", "761163966030151701"))
INTERVAL_DEFAULT_SEC = int(os.environ.get("SATPAMBOT_METRICS_INTERVAL", "60"))

# WIB (UTC+7)
WIB = timezone(timedelta(hours=7), name="WIB")


class LiveMetricsPush(commands.Cog):
    """Collect & publish live metrics to satpambot.dashboard.live_store.STATS."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.loop_task.start()

    def cog_unload(self) -> None:
        try:
            self.loop_task.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=INTERVAL_DEFAULT_SEC)
    async def loop_task(self) -> None:
        guild = None
        try:
            guild = self.bot.get_guild(GUILD_ID_DEFAULT) or await self.bot.fetch_guild(GUILD_ID_DEFAULT)
        except Exception:
            guild = None

        member_count = 0
        online_count = 0

        if guild is not None:
            try:
                member_count = int(getattr(guild, "member_count", 0) or 0)
                if getattr(guild, "chunked", False) and hasattr(guild, "members"):
                    online_count = sum(
                        1 for m in guild.members
                        if getattr(m, "status", discord.Status.offline) != discord.Status.offline
                    )
            except Exception:
                pass

        latency_ms = int((self.bot.latency or 0.0) * 1000)

        cpu = 0.0
        ram = 0.0
        if psutil is not None:
            try:
                cpu = float(psutil.cpu_percent(interval=None))
            except Exception:
                cpu = 0.0
            try:
                proc = psutil.Process()
                ram = float(proc.memory_info().rss) / (1024 * 1024)
            except Exception:
                ram = 0.0

        payload = {
            "member_count": member_count,
            "online_count": online_count,
            "latency_ms": latency_ms,
            "cpu": cpu,
            "ram": ram,
            "ts": datetime.now(WIB).isoformat(timespec="seconds"),
        }

        try:
            from satpambot.dashboard import live_store as _ls  # type: ignore
            _ls.STATS = payload
        except Exception:
            pass

    @loop_task.before_loop
    async def _before_loop(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveMetricsPush(bot))
