# -*- coding: utf-8 -*-
"""
Patch: add start jitter and call the new upsert_pinned_memory which guards 4k limit.
Drop-in for satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner
"""
from __future__ import annotations
import asyncio, random
from discord.ext import tasks, commands
from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory

JITTER_RANGE = (45, 180)  # seconds

class SlangHourlyMiner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_collect.change_interval(seconds=3600)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.loop_collect.is_running():
            self.loop_collect.start()

    @loop_collect.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(*JITTER_RANGE))

    @tasks.loop(seconds=3600.0)
    async def loop_collect(self):
        # ... compute `lingo` as before ...
        lingo = {}  # placeholder: real implementation should fill this dict
        await upsert_pinned_memory(self.bot, {"lingo": lingo})
