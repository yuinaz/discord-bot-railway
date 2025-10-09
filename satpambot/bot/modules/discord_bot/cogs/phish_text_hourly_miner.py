# -*- coding: utf-8 -*-
"""
Patch: add start jitter so it does not collide with slang miner.
Drop-in for satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner
"""
from __future__ import annotations
import asyncio, random
from discord.ext import tasks, commands

JITTER_RANGE = (10, 120)  # seconds (different range)

class PhishTextHourlyMiner(commands.Cog):
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
        # existing mining logic...
        pass
