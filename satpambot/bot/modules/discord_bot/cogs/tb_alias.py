# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

CANDIDATES = ("tempban", "tban", "ban")

class TBAliasCog(commands.Cog):
    """Alias legacy command: !tb -> forwards to tempban/tban/ban (first available).
    This does NOT change config/prefix. It only re-exposes the classic '!tb' name.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tb", help="Alias legacy: tb -> tempban/tban/ban (forwarder)")
    @commands.guild_only()
    async def tb(self, ctx: commands.Context, *args):
        # Try to find an existing command to forward into
        for name in CANDIDATES:
            cmd = self.bot.get_command(name)
            if cmd is not None:
                # Reuse the target command's converters, checks, and error handling
                return await ctx.invoke(cmd, *args)

        # Nothing found: keep behavior explicit but non-fatal
        await ctx.send("⚠️ Target command untuk 'tb' tidak ditemukan (cari: tempban/tban/ban). Cek cogs ban/moderation kamu.", delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(TBAliasCog(bot))
