# -*- coding: utf-8 -*-
from __future__ import annotations
from discord.ext import commands

CANDIDATES = ("ban", "tempban", "tban")

class BanAliasCog(commands.Cog):
    """Alias legacy: !ban -> forwards to ban/tempban/tban (first available).
    Tidak mengubah config/prefix; hanya menyediakan pintu perintah teks !ban.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ban", help="Alias legacy: ban -> ban/tempban/tban (forwarder)")
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, *args):
        for name in CANDIDATES:
            cmd = self.bot.get_command(name)
            if cmd is not None and cmd.name != "ban":  # avoid self-recursion if real 'ban' exists
                return await ctx.invoke(cmd, *args)
            if cmd is not None and cmd.callback is not self.ban.callback:
                return await ctx.invoke(cmd, *args)
        await ctx.send("⚠️ Target command untuk 'ban' tidak ditemukan (cari: ban/tempban/tban). Cek cogs moderasi kamu.", delete_after=10)

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAliasCog(bot))
