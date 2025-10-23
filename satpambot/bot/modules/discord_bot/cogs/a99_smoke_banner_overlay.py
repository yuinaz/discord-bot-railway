# -*- coding: utf-8 -*-
"""
a99_smoke_banner_overlay
Cetak "All cogs loaded OK" di akhir chainloading saat SMOKE_MODE=1.
Tidak mengubah smoke_all.py; hanya mempercantik output agar konsisten dengan format lama.
"""
from discord.ext import commands
import os, logging

log = logging.getLogger(__name__)
SMOKE = (os.getenv("SMOKE_MODE","") == "1")

class SmokeBanner(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        if SMOKE:
            log.info("All cogs loaded OK")
async def setup(bot):
    await bot.add_cog(SmokeBanner(bot))