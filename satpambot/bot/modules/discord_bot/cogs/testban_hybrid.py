# satpambot/bot/modules/discord_bot/cogs/testban_hybrid.py
from __future__ import annotations

import os
import asyncio
import hashlib
from typing import Optional

import discord
from discord.ext import commands

# permissions helper (sudah ada di repo)
from modules.discord_bot.helpers.permissions import is_mod_or_admin
# cari text-channel fleksibel (sudah dipatch sebelumnya)
from ..helpers.log_utils import find_text_channel
from ..utils.actions import delete_message_safe

# === Embed builder (tanpa asset/sticker) ===
def _build_ban_embed(
    guild: Optional[discord.Guild],
    moderator: discord.abc.User,
    target: discord.abc.User,
    reason: str,
    marker: str,
) -> discord.Embed:
    title = "Ban/TestBan Notice"
    desc = (
        f"**User:** {target.mention} (`{getattr(target, 'id', 'unknown')}`)\n"
        f"**Moderator:** {moderator.mention} (`{getattr(moderator, 'id', 'unknown')}`)\n"
        f"**Reason:** {reason.strip() or '—'}"
    )

    color = discord.Color.red()
    if guild and guild.me and hasattr(guild.me, "color") and guild.me.color.value != 0:
        # kalau bot punya peran berwarna, pakai itu biar seragam tema
        color = guild.me.color  # type: ignore

    emb = discord.Embed(title=title, description=desc, color=color)
    emb.set_author(name=getattr(target, "name", "user"), icon_url=getattr(target, "display_avatar", getattr(target, "avatar", None)).url if getattr(getattr(target, "display_avatar", None), "url", None) else discord.Embed.Empty)
    emb.set_footer(text=f"TB_MARKER::{marker}")
    return emb


def _reason_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:8]


async def _find_existing_with_marker(
    channel: discord.TextChannel,
    marker: str,
    *,
    bot_user_id: Optional[int],
    history_limit: int = 50,
) -> Optional[discord.Message]:
    """Cari pesan sebelumnya yang punya footer marker sama (anti-spam)."""
    try:
        async for m in channel.history(limit=history_limit, oldest_first=False):
            # hanya pesan bot sendiri
            if bot_user_id is not None and getattr(m.author, "id", None) != bot_user_id:
                continue
            try:
                if not m.embeds:
                    continue
                ft = getattr(m.embeds[0].footer, "text", "") or ""
                if isinstance(ft, str) and f"TB_MARKER::{marker}" in ft:
                    return m
            except Exception:
                continue
    except Exception:
        pass
    return None


def _resolve_log_channel(ctx: commands.Context, *, name_env: str = "LOG_CHANNEL_NAME", id_env: str = "LOG_CHANNEL_ID") -> Optional[discord.TextChannel]:
    """Ambil channel log dari ENV, kalau tidak, pakai channel saat ini."""
    guild = getattr(ctx, "guild", None)
    if guild is None:
        return None

    cid_raw = os.getenv(id_env) or os.getenv("LOG_CHANNEL_ID_RAW")
    cname = os.getenv(name_env)

    # Coba by ID dulu
    if cid_raw and cid_raw.strip().isdigit():
        ch = find_text_channel(guild, channel_id=int(cid_raw.strip()))
        if ch:
            return ch  # type: ignore

    # Lalu by name
    if cname and cname.strip():
        ch = find_text_channel(guild, name=cname.strip())
        if ch:
            return ch  # type: ignore

    # Fallback: current channel jika text
    if getattr(ctx.channel, "type", None) and getattr(ctx.channel.type, "text", False):
        return ctx.channel  # type: ignore

    # Cari text channel pertama yg bisa kirim
    return find_text_channel(guild)


class TestBanHybrid(commands.Cog):
    """Post embed TestBan (tanpa sticker), dedupe by marker, hybrid command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="tb", description="Post test ban embed (no image, no spam).")
    @commands.check(is_mod_or_admin)
    async def tb(self, ctx: commands.Context, target: Optional[discord.User] = None, *, reason: str = "Spam/Phishing"):
        """
        Contoh pakai:
          - !tb @user alasan…
          - /tb target:@user reason:alasan

        Tidak ada aksi ban sungguhan, hanya kirim embed ke channel log (atau channel saat ini).
        Anti-duplikat: jika marker sama, pesan lama akan di-edit bukan dibuat baru.
        """
        # Validasi target
        if target is None:
            # kalau tidak ada, coba ambil dari mention manual text command
            if ctx.message and ctx.message.mentions:
                target = ctx.message.mentions[0]
            else:
                await ctx.reply("❗ Beri user target. Contoh: `!tb @user [alasan]`", mention_author=False)
                return

        guild = getattr(ctx, "guild", None)
        ch = _resolve_log_channel(ctx)
        if ch is None:
            await ctx.reply("❗ Tidak menemukan channel log yang valid.", mention_author=False)
            return

        moderator = getattr(ctx, "author", None) or getattr(ctx, "user", None) or self.bot.user
        marker = f"{getattr(target, 'id', '0')}|{_reason_hash(reason)}"
        emb = _build_ban_embed(guild, moderator, target, reason, marker)

        # deteksi pesan lama & edit untuk dedupe
        bot_user_id = getattr(getattr(ctx, "me", None) or getattr(self.bot, "user", None), "id", None)
        old = await _find_existing_with_marker(ch, marker, bot_user_id=bot_user_id)

        if old:
            try:
                await old.edit(embed=emb)
                sent = old
                action = "updated"
            except Exception:
                sent = await ch.send(embed=emb)
                action = "sent"
        else:
            sent = await ch.send(embed=emb)
            action = "sent"

        # Rapikan command message agar channel bersih (jika prefix command)
        try:
            if ctx.message and ctx.guild and ctx.channel.id != sent.channel.id:
                # kalau kirimnya di channel lain, biarkan pesan command utuh
                pass
            else:
                # hapus command user (tidak fatal kalau gagal)
                await delete_message_safe(ctx.message)
        except Exception:
            pass

        # balas singkat tanpa ping
        try:
            await ctx.reply(f"✅ TestBan {action} → {sent.jump_url}", mention_author=False, delete_after=8)
        except Exception:
            pass  # diam kalau tidak bisa reply (misal dipanggil via slash dan sudah ada response)


async def setup(bot: commands.Bot):
    await bot.add_cog(TestBanHybrid(bot))