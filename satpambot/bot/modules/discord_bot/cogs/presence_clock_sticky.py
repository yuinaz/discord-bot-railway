from __future__ import annotations
import os, datetime
import pytz
import discord
from discord.ext import commands, tasks

TZ = os.getenv("STICKY_CLOCK_TZ","Asia/Jakarta")

class PresenceClockSticky(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_min = None
        self.loop.start()

    @tasks.loop(seconds=30)
    async def loop(self):
        try:
            tz = pytz.timezone(TZ)
            now = datetime.datetime.now(tz)
            m = now.minute
            if m == self._last_min:
                return
            self._last_min = m
            text = f"Online • {now:%H:%M}"
            await self.bot.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.watching, name=text)
            )
        except Exception:
            pass

    @loop.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

async def setup(bot): await bot.add_cog(PresenceClockSticky(bot))