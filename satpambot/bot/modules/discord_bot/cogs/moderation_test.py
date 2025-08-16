# satpambot/bot/modules/discord_bot/cogs/moderation_test.py
from __future__ import annotations

import discord
from discord.ext import commands
from typing import Optional

# Pakai checker yang sudah ada di repo kamu
from modules.discord_bot.helpers.permissions import is_mod_or_admin


class ModerationTest(commands.Cog):
    """Cog uji fitur moderasi. Semua output embed-only (tanpa gambar/sticker)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="mt_embed", help="Kirim embed uji coba")
    @commands.check(is_mod_or_admin)
    async def mt_embed(self, ctx: commands.Context, *, reason: str = "Test embed"):
        embed = discord.Embed(
            title="✅ Test Embed",
            description=reason,
            colour=discord.Colour.green(),
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(name="mt_tb", help="Simulasi testban (embed-only)")
    @commands.check(is_mod_or_admin)
    async def mt_tb(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: str = "Testban",
    ):
        target = member.mention if isinstance(member, discord.Member) else "—"
        embed = discord.Embed(
            title="🚧 Testban (embed-only)",
            description=f"Target: {target}\nReason: {reason}",
            colour=discord.Colour.orange(),
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    """Entry point standar untuk discord.py extensions."""
    await bot.add_cog(ModerationTest(bot))
