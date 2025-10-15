from __future__ import annotations

import inspect
from typing import Optional
import discord
from discord.ext import commands

LOG_CHANNEL_NAME = "log-botphising"

BLOCK_MODULE_SUBSTR = [
    "cogs/phash_auto_ban.py",
    "cogs/anti_image_phish_guard.py",
    "cogs/anti_image_phish_advanced.py",
    "cogs/anti_image_phish_signature.py",
    "cogs/fast_raid_autoban.py",
]

ALLOW_MODULE_SUBSTR = [
    "cogs/mod_ban_basic.py",
    "cogs/ban_alias.py",
    "cogs/ban_secure.py",
    "cogs/moderation_extras.py",
    "cogs/ban_logger.py",
]

ALLOW_REASON_SUBSTR = "Anti-Image Guard (armed)"

def _should_block() -> bool:
    frames = inspect.stack()
    srcs = [ (f.filename or "") for f in frames ]
    if any(any(x in s for x in ALLOW_MODULE_SUBSTR) for s in srcs):
        return False
    if any(any(x in s for x in BLOCK_MODULE_SUBSTR) for s in srcs):
        return True
    return False

def _find_log_channel(guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
    if guild is None: return None
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME and ch.permissions_for(guild.me).send_messages:
            return ch
    for ch in guild.text_channels:
        if ch.permissions_for(guild.me).send_messages:
            return ch
    return None

_orig_member_ban = discord.Member.ban
_orig_guild_ban = discord.Guild.ban

async def _safe_member_ban(self: discord.Member, *args, **kwargs):
    reason = kwargs.get("reason")
    if reason and ALLOW_REASON_SUBSTR in str(reason):
        return await _orig_member_ban(self, *args, **kwargs)
    if _should_block():
        try:
            ch = _find_log_channel(self.guild)
            if ch:
                src = next((f.filename for f in inspect.stack() if f and f.filename), "?")
                await ch.send(embed=discord.Embed(
                    title="Auto-ban blocked",
                    description=f"Blocked **auto-ban** call from `{src}` for user {self.mention}.",
                    color=discord.Color.gold()
                ), silent=True)
        except Exception: pass
        return None
    return await _orig_member_ban(self, *args, **kwargs)

async def _safe_guild_ban(self: discord.Guild, user: discord.abc.Snowflake, *args, **kwargs):
    reason = kwargs.get("reason")
    if reason and ALLOW_REASON_SUBSTR in str(reason):
        return await _orig_guild_ban(self, user, *args, **kwargs)
    if _should_block():
        try:
            ch = _find_log_channel(self)
            if ch:
                src = next((f.filename for f in inspect.stack() if f and f.filename), "?")
                await ch.send(embed=discord.Embed(
                    title="Auto-ban blocked",
                    description=f"Blocked **auto-ban** call from `{src}` for user `{getattr(user, 'id', user)}`.",
                    color=discord.Color.gold()
                ), silent=True)
        except Exception: pass
        return None
    return await _orig_guild_ban(self, user, *args, **kwargs)

discord.Member.ban = _safe_member_ban
discord.Guild.ban = _safe_guild_ban

class AutobanSafetyInterceptor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(AutobanSafetyInterceptor(bot))