from __future__ import annotations

import datetime as _dt
from typing import Optional

import discord
from discord.ext import commands

WIB = _dt.timezone(_dt.timedelta(hours=7))

def _wib_now_str() -> str:
    return _dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

class HelpBasic(commands.Cog):
    """Help command (prefix) with a compact embed. Safe to load in any environment."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_cmd(self, ctx: commands.Context) -> None:
        """Show prefix help for moderators."""
        e = discord.Embed(
            title="📘 Bantuan — Prefix Commands",
            description=(
                "Ringkasan perintah moderasi yang tersedia.\n"
                "Gunakan **/** untuk perintah slash (jika ada)."
            ),
        )
        e.add_field(
            name="💀 Simulasi Ban — `!tb`",
            value=(
                "Simulasi tanpa aksi nyata. Bisa **reply** ke pesan lalu ketik "
                "`!tb [alasan?]`, atau `!tb @user [alasan]`. Hasil embed "
                "menampilkan **Lokasi**, **Alasan**, dan timestamp **WIB**.\n"
                "Contoh: `!tb` *(sambil reply pesan)*"
            ),
            inline=False,
        )
        e.add_field(
            name="🔨 Ban — `!ban`",
            value=(
                "Ban permanen. Bot membutuhkan permission ban pada server & channel ini.\n"
                "Contoh: `!ban @user promosi phishing`"
            ),
            inline=False,
        )
        e.set_footer(text=f"SatpamBot Help • {_wib_now_str()}")
        await ctx.reply(embed=e, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpBasic(bot))
