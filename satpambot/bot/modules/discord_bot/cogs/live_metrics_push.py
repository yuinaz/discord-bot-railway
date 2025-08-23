# satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from discord.ext import commands, tasks
import discord

TZ_WIB = timezone(timedelta(hours=7), name="WIB")

def _status_online(status: discord.Status) -> bool:
    return status in (discord.Status.online, discord.Status.idle, discord.Status.dnd)

class LiveMetricsPush(commands.Cog):
    """Single-process: langsung update satpambot.dashboard.live_store.STATS."""
    def __init__(self, bot: commands.Bot, interval: int = 30):
        self.bot = bot
        self.push_loop.change_interval(seconds=max(5, interval))
        self.push_loop.start()

    def cog_unload(self):
        self.push_loop.cancel()

    def _collect(self) -> dict:
        guilds = len(self.bot.guilds)
        members = 0
        online  = 0
        channels= 0
        threads = 0

        for g in self.bot.guilds:
            try:
                members += int(getattr(g, "member_count", 0) or 0)
            except Exception:
                pass
            try:
                channels += len(g.channels)
            except Exception:
                pass
            try:
                threads += len(getattr(g, "threads", []) or [])
            except Exception:
                pass
            try:
                for m in getattr(g, "members", []):
                    if _status_online(getattr(m, "status", discord.Status.offline)):
                        online += 1
            except Exception:
                pass

        latency_ms = int((self.bot.latency or 0.0) * 1000)
        return {
            "guilds": guilds,
            "members": members,
            "online": online,
            "channels": channels,
            "threads": threads,
            "latency_ms": latency_ms,
        }

    @tasks.loop(seconds=30)
    async def push_loop(self):
        payload = self._collect()
        try:
            from satpambot.dashboard import live_store as _ls  # type: ignore
            _ls.STATS = {
                **payload,
                "ts": int(datetime.now(TZ_WIB).timestamp()),
            }
            # print("[metrics] live_store update OK")  # optional log
        except Exception as e:
            print(f"[metrics] live_store error: {e}")

    @push_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

# Loader kompatibel
async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMetricsPush(bot))

def setup(bot: commands.Bot):
    bot.add_cog(LiveMetricsPush(bot))
