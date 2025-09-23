
from __future__ import annotations
import os, asyncio, datetime
from collections import defaultdict
import discord
from discord.ext import commands

# ===== ENV (match your .env) =====
def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default

LOG_CHANNEL_ID = _get_int_env("LOG_CHANNEL_ID", _get_int_env("LOG_CHANNEL_ID_RAW", 0))
SUPPRESS_S = 5                  # dedup window vs mod-log (constant; no new ENV)
WAIT_BEFORE_CHECK_MS = 1000     # small delay to let mod-log come first

# ===== Last-seen tracker (TextChannel only) =====
_LAST_SEEN: dict[int, dict[int, tuple[int, int, datetime.datetime]]] = {}
_SEEN_TTL = datetime.timedelta(hours=24)

def _utcnow():
    return discord.utils.utcnow()

def _fmt(dt: datetime.datetime) -> str:
    return dt.strftime("SatpamBot • %Y-%m-%d %H:%M:%S")

async def _get_log_channel(guild: discord.Guild) -> discord.abc.GuildChannel | None:
    return guild.get_channel(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None

async def _modlog_has_recent_ban(guild: discord.Guild, user: discord.abc.User) -> bool:
    if not LOG_CHANNEL_ID:
        return False
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if not ch or not isinstance(ch, (discord.TextChannel, discord.Thread)):
        return False
    after = _utcnow() - datetime.timedelta(seconds=SUPPRESS_S)
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

def _last_seen_textchannel(guild: discord.Guild, user_id: int) -> discord.TextChannel | None:
    entries = _LAST_SEEN.get(guild.id, {})
    entry = entries.get(user_id)
    if not entry:
        return None
    ch_id, _msg_id, ts = entry
    if _utcnow() - ts > _SEEN_TTL:
        return None
    ch = guild.get_channel(ch_id)
    if isinstance(ch, discord.TextChannel):
        return ch
    return None

def _can_send(ch: discord.TextChannel, me: discord.Member) -> bool:
    try:
        perms = ch.permissions_for(me)
        return bool(perms.view_channel and perms.send_messages)
    except Exception:
        return False

def _build_embed(user: discord.abc.User, reason: str, actor: str, where: discord.TextChannel | None):
    embed = discord.Embed(
        title="💀 Ban Otomatis oleh SatpamBot",
        description=f"{user.mention} telah diban otomatis.",
        color=discord.Color.red()
    )
    if where:
        embed.add_field(name="Lokasi Touchdown", value=where.mention, inline=False)
    embed.add_field(name="Moderator", value=actor, inline=True)
    embed.add_field(name="Alasan", value=reason, inline=True)
    embed.set_footer(text=_fmt(_utcnow()))
    return embed

class BanAutoEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        # Track only TextChannel last seen
        if not msg.guild or msg.author.bot:
            return
        if isinstance(msg.channel, discord.TextChannel):
            _LAST_SEEN.setdefault(msg.guild.id, {})[msg.author.id] = (
                msg.channel.id, msg.id, _utcnow()
            )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # let mod-log post first
        if WAIT_BEFORE_CHECK_MS > 0:
            await asyncio.sleep(WAIT_BEFORE_CHECK_MS / 1000)

        reason = await _get_ban_reason(guild, user)
        actor  = await _get_actor_text(self.bot, guild, user)

        me = guild.me or await guild.fetch_member(self.bot.user.id)
        td = _last_seen_textchannel(guild, user.id)
        embed = _build_embed(user, reason, actor, td)

        # 1) Touchdown TextChannel
        if td and _can_send(td, me):
            try:
                await td.send(embed=embed)
            except Exception:
                pass

        # 2) LOG channel (per your ENV)
        log = await _get_log_channel(guild)
        if log and isinstance(log, (discord.TextChannel, discord.Thread)):
            try:
                if not await _modlog_has_recent_ban(guild, user):
                    await log.send(embed=_build_embed(user, reason, actor, td))
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAutoEmbed(bot))
