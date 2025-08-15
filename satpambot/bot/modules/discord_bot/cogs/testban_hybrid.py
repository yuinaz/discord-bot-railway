from __future__ import annotations
from typing import Optional

import discord
from discord import app_commands
from ..helpers.ban_embed import build_ban_embed
from discord.ext import commands

from modules.discord_bot.helpers.permissions import is_mod_or_admin

def _allowed_mentions_for(target: Optional[discord.Member]) -> discord.AllowedMentions:
    return discord.AllowedMentions(
        users=[target] if target else [], roles=False, everyone=False, replied_user=False
    )

class TestbanHybrid(commands.Cog):
    """Hybrid command /testban dan !tb (simulasi ban)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_embed(self, ctx: commands.Context, embed: discord.Embed, *, allowed: discord.AllowedMentions):
        try:
            if getattr(ctx, "interaction", None) and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(embed=embed, allowed_mentions=allowed)
            else:
                await ctx.send(embed=embed, allowed_mentions=allowed)
        except Exception:
            try:
                await ctx.channel.send(embed=embed, allowed_mentions=allowed)
            except Exception:
                pass

    async def _simulate(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        author = ctx.author if isinstance(ctx.author, discord.Member) else None
        if not author or not is_mod_or_admin(author):
            msg = "❌ Kamu tidak punya izin untuk menjalankan perintah ini."
            if getattr(ctx, "interaction", None) and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        target: Optional[discord.Member] = member or (author if isinstance(author, discord.Member) else None)
        if target is None:
            msg = "❌ Tidak bisa menentukan target."
            if getattr(ctx, "interaction", None) and not ctx.interaction.response.is_done():
                await ctx.interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        # === EMBED persis seperti request ===
        embed = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot",
            description=(
                f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n\n"
                "(Pesan ini hanya simulasi untuk pengujian.)"
            ),
            color=discord.Color.orange()
        )
        # Baris paling bawah
        embed.add_field(name="\u200b", value="🧪 Simulasi testban", inline=False)

        await self._send_embed(ctx, embed, allowed=_allowed_mentions_for(target))

    # ===== Commands =====

    @commands.hybrid_command(
        name="testban",
        description="Simulasi ban (hanya menampilkan embed simulasi).",
        with_app_command=True,
        aliases=["tb"]
    )
    async def testban_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._simulate(ctx, member)

    # Slash alias eksplisit: /tb
    @app_commands.command(name="tb", description="Alias dari /testban")
    async def testban_slash_alias(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        # gunakan embed layout seragam
        try:
            _target = (member if 'member' in locals() else ctx.author)
            _emb = build_ban_embed(_target, simulated=True)
            await ctx.send(embed=_emb)
            return
        except Exception:
            pass
    # dedupe guard untuk !tb
    try:
        from ..helpers.once import once as _once
        if ctx and hasattr(ctx, 'message'):
            _key = f"tb:{ctx.guild.id}:{ctx.channel.id}:{ctx.message.id}"
            if not await _once(_key, ttl=8):
                return
    except Exception:
        pass
        ctx = await commands.Context.from_interaction(interaction)
        await self._simulate(ctx, member)

async def setup(bot: commands.Bot):
    # cegah duplikasi command dari cog lain
    try:
        bot.remove_command("testban")
        bot.remove_command("tb")
    except Exception:
        pass
    await bot.add_cog(TestbanHybrid(bot))
