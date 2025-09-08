
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as _dt
from typing import Optional
import discord
from discord.ext import commands

WIB_OFFSET = _dt.timedelta(hours=7)

def _now_wib() -> _dt.datetime:
    # Gunakan aware utc + offset 7 jam (tanpa dependensi eksternal)
    return _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc) + WIB_OFFSET

def _fmt_wib(dt: Optional[_dt.datetime] = None) -> str:
    if dt is None:
        dt = _now_wib()
    # 2025-09-08 22:17:07 WIB
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " WIB"

class TBShimFormatted(commands.Cog):
    """Simulasi testban dengan format embed yang konsisten."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tb", aliases=["testban"], help="Simulasi ban (tidak ada aksi nyata).")
    @commands.guild_only()
    async def tb(self, ctx: commands.Context, *, reason: str = ""):
        # Tentukan target:
        target_mention = None
        ref_msg: Optional[discord.Message] = None

        # 1) Jika command berupa reply ke sebuah pesan, gunakan author pesan tsb sebagai target mention
        if ctx.message.reference and isinstance(ctx.message.reference.resolved, discord.Message):
            ref_msg = ctx.message.reference.resolved
            if ref_msg and ref_msg.author:
                target_mention = ref_msg.author.mention

        # 2) Jika ada mention eksplisit di perintah, pakai yang pertama
        if not target_mention and ctx.message.mentions:
            target_mention = ctx.message.mentions[0].mention

        # 3) Fallback
        if not target_mention:
            target_mention = "(tidak ada target)"

        # Build embed
        title = "💀 Simulasi Ban oleh SatpamBot"
        desc_lines = [f"{target_mention} terdeteksi mengirim pesan mencurigakan.", "(Pesan ini hanya simulasi untuk pengujian.)"]
        embed = discord.Embed(
            title=title,
            description="\n".join(desc_lines),
            colour=discord.Colour.blurple(),
        )
        # Lokasi & alasan
        ch_name = f"{ctx.channel.mention}"
        embed.add_field(name="Lokasi", value=ch_name, inline=False)
        embed.add_field(name="Alasan", value=reason or "-", inline=False)

        # Footer sesuai contoh + WIB di footer
        embed.set_footer(text="Simulasi testban • Tidak ada aksi nyata yang dilakukan • " + _fmt_wib())

        # Kirim sebagai balasan ke pesan referensi jika ada, supaya UI mirip contoh
        try:
            if ref_msg:
                await ref_msg.reply(embed=embed)
            else:
                await ctx.reply(embed=embed)
        except discord.HTTPException:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TBShimFormatted(bot))
