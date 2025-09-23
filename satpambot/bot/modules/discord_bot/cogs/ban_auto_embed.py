from __future__ import annotations
import os, asyncio, datetime, re
import discord
from discord.ext import commands

def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default

BAN_PUBLIC_SUPPRESS_S = _get_int_env("BAN_PUBLIC_SUPPRESS_S", 5)
BAN_PUBLIC_WAIT_BEFORE_CHECK_MS = _get_int_env("BAN_PUBLIC_WAIT_BEFORE_CHECK_MS", 1000)
BAN_PUBLIC_CHANNEL_ID = _get_int_env("BAN_PUBLIC_CHANNEL_ID", 0)
LOG_CHANNEL_ID = _get_int_env("LOG_CHANNEL_ID", _get_int_env("LOG_CHANNEL_ID_RAW", 0))

def _utcnow():
    return discord.utils.utcnow()

def _fmt_wib(dt: datetime.datetime) -> str:
    return dt.strftime("SatpamBot • %Y-%m-%d %H:%M:%S WIB")

async def _get_public_channel(guild: discord.Guild):
    ch = guild.get_channel(BAN_PUBLIC_CHANNEL_ID) if BAN_PUBLIC_CHANNEL_ID else None
    if ch:
        return ch
    if LOG_CHANNEL_ID:
        return guild.get_channel(LOG_CHANNEL_ID)
    return None

async def _modlog_has_recent_ban(guild: discord.Guild, user: discord.abc.User) -> bool:
    if not LOG_CHANNEL_ID:
        return False
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if not ch or not isinstance(ch, (discord.TextChannel, discord.Thread)):
        return False
    after = _utcnow() - datetime.timedelta(seconds=BAN_PUBLIC_SUPPRESS_S)
    uid = str(user.id)
    async for m in ch.history(limit=25, after=after, oldest_first=False):
        if uid in (m.content or ""):
            return True
        for e in (m.embeds or []):
            blob = (e.title or "") + (e.description or "")
            for f in (e.fields or []):
                blob += (f.name or "") + (f.value or "")
            if uid in blob:
                return True
    return False

async def _get_ban_reason(guild: discord.Guild, user: discord.abc.User) -> str:
    try:
        ban = await guild.fetch_ban(user)
        if ban and ban.reason:
            return ban.reason
    except Exception:
        pass
    return "—"

async def _get_actor_text(bot: commands.Bot, guild: discord.Guild, user: discord.abc.User) -> str:
    after = _utcnow() - datetime.timedelta(seconds=45)
    try:
        async for entry in guild.audit_logs(limit=8, action=discord.AuditLogAction.ban, after=after):
            if entry.target and entry.target.id == user.id:
                if entry.user and bot.user and entry.user.id == bot.user.id:
                    return "SatpamBot (auto)"
                return entry.user.mention if entry.user else "System"
    except Exception:
        pass
    return "System"

class BanAutoEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if BAN_PUBLIC_WAIT_BEFORE_CHECK_MS > 0:
            await asyncio.sleep(BAN_PUBLIC_WAIT_BEFORE_CHECK_MS / 1000)

        channel = await _get_public_channel(guild)
        if not channel:
            return

        try:
            if await _modlog_has_recent_ban(guild, user):
                return
        except Exception:
            pass

        reason = await _get_ban_reason(guild, user)
        actor  = await _get_actor_text(self.bot, guild, user)

        embed = discord.Embed(
            title="💀 Ban Otomatis oleh SatpamBot",
            description=f"{user.mention} telah diban secara otomatis oleh sistem.",
            color=discord.Color.red()
        )
        embed.add_field(name="Moderator", value=actor, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=True)
        embed.set_footer(text=_fmt_wib(_utcnow()))
        try:
            await channel.send(embed=embed)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAutoEmbed(bot))
