# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as _dt
from typing import Optional

import discord
from discord.ext import commands

WIB = _dt.timezone(_dt.timedelta(hours=7))

def fmt_wib(dt: Optional[_dt.datetime] = None) -> str:
    if dt is None:
        dt = _dt.datetime.now(tz=WIB)
    return dt.strftime("%Y-%m-%d %H:%M:%S WIB")

class TBEnforcerUnique(commands.Cog):
    """
    Pastikan hanya satu perintah prefix `!tb` yang aktif.
    Tidak menyentuh config; idempoten; aman di-reload.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cmd_obj: Optional[commands.Command] = None

    async def cog_unload(self):
        if self._cmd_obj:
            try:
                self.bot.remove_command("tb")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        # enforce setiap kali on_ready (idempoten)
        await self._ensure_unique()

    async def _ensure_unique(self):
        # Hapus semua 'tb' yang sudah ada
        try:
            while self.bot.get_command("tb") is not None:
                self.bot.remove_command("tb")
        except Exception:
            # tetap lanjut
            pass

        # Tambahkan 'tb' simulasi stabil
        self._cmd_obj = commands.Command(self._tb_impl, name="tb",
                                         help="Simulasi ban (tidak ada aksi nyata).")
        try:
            self.bot.add_command(self._cmd_obj)
        except Exception:
            # jika race condition, reset sekali lagi
            try:
                while self.bot.get_command("tb") is not None:
                    self.bot.remove_command("tb")
                self.bot.add_command(self._cmd_obj)
            except Exception:
                pass

    async def _tb_impl(self, ctx: commands.Context, *, reason: str = ""):
        # Tentukan target: reply > mention > author
        author = None
        if ctx.message.reference and ctx.message.reference.resolved:
            try:
                ref = ctx.message.reference.resolved
                author = ref.author.mention if hasattr(ref, "author") else None
            except Exception:
                author = None
        if not author and ctx.message.mentions:
            author = ctx.message.mentions[0].mention
        if not author:
            author = ctx.author.mention

        title = "💀 Simulasi Ban oleh SatpamBot"
        desc_lines = [
            f"{author} terdeteksi mengirim pesan mencurigakan.",
            "(Pesan ini hanya simulasi untuk pengujian.)",
        ]
        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            colour=discord.Colour.dark_grey(),
        )
        ch_text = f"#{getattr(ctx.channel, 'name', 'unknown')}"                   if isinstance(ctx.channel, discord.TextChannel) else str(ctx.channel)
        if reason:
            embed.add_field(name="Alasan", value=reason, inline=False)
        embed.add_field(name="Lokasi", value=ch_text, inline=False)
        embed.set_footer(text="Simulasi testban • Tidak ada aksi nyata yang dilakukan • " + fmt_wib())

        try:
            await ctx.reply(embed=embed, mention_author=False)
        except Exception:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TBEnforcerUnique(bot))
