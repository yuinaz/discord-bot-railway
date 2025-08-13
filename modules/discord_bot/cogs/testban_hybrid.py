from __future__ import annotations
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class TestbanHybrid(commands.Cog):
    """Hybrid command /testban dan /tb dengan layout persis sesuai contoh."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_embed(self, ctx: commands.Context, embed: discord.Embed, *, allowed: discord.AllowedMentions):
        # dukung prefix & slash
        try:
            if getattr(ctx, "interaction", None) and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(embed=embed, allowed_mentions=allowed)
            else:
                await ctx.reply(embed=embed, mention_author=False, allowed_mentions=allowed)
        except discord.HTTPException:
            await ctx.send(embed=embed, allowed_mentions=allowed)

    async def _simulate(self, ctx: commands.Context, member: Optional[discord.Member]):
        target: Optional[discord.Member] = member or (ctx.author if isinstance(ctx.author, discord.Member) else None)
        if target is None:
            if getattr(ctx, "interaction", None) and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message("❌ Tidak bisa menentukan target.", ephemeral=True)
            else:
                await ctx.send("❌ Tidak bisa menentukan target.")
            return

        # === EMBED persis seperti yang diminta ===
        embed = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot",
            description=(
                f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n\n"
                "(Pesan ini hanya simulasi untuk pengujian.)"
            ),
            color=discord.Color.orange()
        )
        # Baris terakhir:
        embed.add_field(name="\u200b", value="🧪 Simulasi testban", inline=False)

        allowed = discord.AllowedMentions(
            users=[target], roles=False, everyone=False, replied_user=False
        )
        await self._send_embed(ctx, embed, allowed=allowed)

    # ===== Commands =====

    @commands.hybrid_command(
        name="testban",
        description="Simulasi ban (hanya menampilkan embed simulasi).",
        with_app_command=True,
        aliases=["tb"]
    )
    @commands.has_permissions(ban_members=True)
    async def testban_hybrid(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._simulate(ctx, member)

    # Slash alias eksplisit: /tb
    @app_commands.command(name="tb", description="Alias dari /testban")
    @app_commands.checks.has_permissions(ban_members=True)
    async def testban_slash_alias(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        ctx = await commands.Context.from_interaction(interaction)
        await self._simulate(ctx, member)

async def setup(bot: commands.Bot):
    try:
        bot.remove_command("testban")  # hindari duplikasi dari cog lain
    except Exception:
        pass
    await bot.add_cog(TestbanHybrid(bot))
