# satpambot/bot/modules/discord_bot/cogs/image_poster.py
# Embed-only, aman tanpa aset. Jika cog ini tak dipakai, biarkan saja.
from __future__ import annotations

from typing import Optional
import discord
from discord.ext import commands

from modules.discord_bot.helpers.ban_embed import build_ban_embed, reason_hash
from modules.discord_bot.helpers.log_utils import find_text_channel

class ImagePoster(commands.Cog):
    """Poster ringan tanpa gambar (fallback)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="poster")
    @commands.has_permissions(manage_messages=True)
    async def poster(self, ctx: commands.Context, *, reason: str = "Info"):
        """Demo poster (embed-only)."""
        guild = ctx.guild
        ch: Optional[discord.TextChannel] = None
        if guild:
            ch = find_text_channel(guild)  # pakai channel teks pertama yang bisa kirim
        if ch is None and isinstance(ctx.channel, discord.TextChannel):
            ch = ctx.channel

        if ch is None:
            await ctx.reply("❗ Tidak menemukan channel untuk mengirim poster.", mention_author=False)
            return

        marker = f"poster|{reason_hash(reason)}"
        emb = build_ban_embed(
            guild=guild,
            moderator=getattr(ctx, "author", self.bot.user),
            target=getattr(ctx, "author", self.bot.user),
            reason=reason,
            marker=marker,
        )
        emb.title = "Information"
        await ch.send(embed=emb)
        try:
            await ctx.message.delete()
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ImagePoster(bot))
