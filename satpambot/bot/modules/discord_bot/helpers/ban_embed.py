# satpambot/bot/modules/discord_bot/helpers/ban_embed.py
from __future__ import annotations

import hashlib
from typing import Optional
import discord

def _avatar_url(user: discord.abc.User) -> Optional[str]:
    try:
        if getattr(getattr(user, "display_avatar", None), "url", None):
            return user.display_avatar.url  # type: ignore
        if getattr(getattr(user, "avatar", None), "url", None):
            return user.avatar.url  # type: ignore
    except Exception:
        pass
    return None

def _color_from_guild(guild: Optional[discord.Guild]) -> discord.Color:
    try:
        if guild and guild.me and getattr(guild.me, "color", None) and guild.me.color.value != 0:
            return guild.me.color  # type: ignore
    except Exception:
        pass
    return discord.Color.red()

def reason_hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8", "ignore")).hexdigest()[:8]

def build_ban_embed(
    *,
    guild: Optional[discord.Guild],
    moderator: discord.abc.User,
    target: discord.abc.User,
    reason: str,
    marker: str,
) -> discord.Embed:
    """
    Embed BAN/TestBan seragam—tanpa gambar/sticker, ringan.
    Footer menyimpan marker untuk dedupe.
    """
    desc = (
        f"**User:** {target.mention} (`{getattr(target, 'id', 'unknown')}`)\n"
        f"**Moderator:** {moderator.mention} (`{getattr(moderator, 'id', 'unknown')}`)\n"
        f"**Reason:** {reason.strip() or '—'}"
    )
    emb = discord.Embed(
        title="Ban/TestBan Notice",
        description=desc,
        color=_color_from_guild(guild),
    )
    av = _avatar_url(target)
    if av:
        emb.set_author(name=getattr(target, "name", "user"), icon_url=av)
    else:
        emb.set_author(name=getattr(target, "name", "user"))
    emb.set_footer(text=f"BAN_MARKER::{marker}")
    return emb
