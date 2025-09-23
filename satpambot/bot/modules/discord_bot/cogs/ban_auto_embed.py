
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
SUPPRESS_S = 5                  # dedup window vs mod-log
WAIT_BEFORE_CHECK_MS = 1000     # small delay to let mod-log post first

# ===== Last-seen tracker (TextChannel only) =====
_LAST_SEEN: dict[int, dict[int, tuple[int, int, datetime.datetime]]] = {}
_SEEN_TTL = datetime.timedelta(hours=24)

def _utcnow():
    return discord.utils.utcnow()

def _fmt(dt: datetime.datetime) -> str:
    return dt.strftime("SatpamBot • %Y-%m-%d %H:%M:%S")

def _casefold(s: str) -> str:
    return s.casefold()

async def _get_log_target(guild: discord.Guild):
    """
    Return where to post according to ENV:
    - If LOG_CHANNEL_ID points to a Thread -> use that Thread.
    - Else if it points to a TextChannel:
        - Prefer an active thread whose name contains 'ban log' (case-insensitive).
        - Otherwise, use the TextChannel itself.
    """
    if not LOG_CHANNEL_ID:
        return None
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if isinstance(ch, discord.Thread):
        return ch
    if isinstance(ch, discord.TextChannel):
        try:
            name_key = _casefold("ban log")
            for t in ch.threads:
                if t.archived:
                    continue
                if name_key in _casefold(t.name):
                    return t
        except Exception:
            pass
        return ch
    return None

async def _modlog_has_recent_ban(guild: discord.Guild, user: discord.abc.User) -> bool:
    if not LOG_CHANNEL_ID:
        return False
    target = await _get_log_target(guild)
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        return False
    after = _utcnow() - datetime.timedelta(seconds=SUPPRESS_S)
    uid = str(user.id)
    try:
        async for m in target.history(limit=25, after=after, oldest_first=False):
            if uid in (m.content or ""):
                return True
            for e in (m.embeds or []):
                blob = (e.title or "") + (e.description or "")
                for f in (e.fields or []):
                    blob += (f.name or "") + (f.value or "")
                if uid in blob:
                    return True
    except Exception:
        pass
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
    entry = _LAST_SEEN.get(guild.id, {}).get(user_id)
    if not entry:
        return None
    ch_id, _msg_id, ts = entry
    if _utcnow() - ts > _SEEN_TTL:
        return None
    ch = guild.get_channel(ch_id)
    if isinstance(ch, discord.TextChannel):
        return ch
    return None

def _can_send(ch: discord.abc.GuildChannel, me: discord.Member) -> bool:
    try:
        perms = ch.permissions_for(me)
        return bool(perms.view_channel and perms.send_messages)
    except Exception:
        return False

def _embed_touchdown(user: discord.abc.User, where: discord.TextChannel | None, reason: str, actor: str):
    # Richer embed for the public touchdown channel
    embed = discord.Embed(
        title="💀 Ban Otomatis oleh SatpamBot",
        description=f"{user.mention} telah diban otomatis.",
        color=discord.Color.red()
    )
    if where:
        embed.add_field(name="Lokasi Touchdown", value=where.mention, inline=False)
    if reason and reason != "—":
        embed.add_field(name="Alasan", value=reason, inline=True)
    embed.add_field(name="Moderator", value=actor, inline=True)
    embed.set_footer(text=_fmt(_utcnow()))
    return embed

def _embed_log_simple(user: discord.abc.User):
    # Minimal embed like your screenshot
    tag = f"{user.name} ({user.id})"
    embed = discord.Embed(title="Banned", description=tag, color=discord.Color.dark_grey())
    return embed

class BanAutoEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Track last seen ONLY for TextChannel (ignore threads)
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not msg.guild or msg.author.bot:
            return
        if isinstance(msg.channel, discord.TextChannel):
            _LAST_SEEN.setdefault(msg.guild.id, {})[msg.author.id] = (msg.channel.id, msg.id, _utcnow())

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if WAIT_BEFORE_CHECK_MS > 0:
            await asyncio.sleep(WAIT_BEFORE_CHECK_MS / 1000)

        reason = await _get_ban_reason(guild, user)
        actor  = await _get_actor_text(self.bot, guild, user)
        me = guild.me or await guild.fetch_member(self.bot.user.id)

        td = _last_seen_textchannel(guild, user.id)

        # 1) Touchdown (TextChannel) — richer embed
        if td and _can_send(td, me):
            try:
                await td.send(embed=_embed_touchdown(user, td, reason, actor))
            except Exception:
                pass

        # 2) LOG channel or its 'Ban Log' thread — SIMPLE embed
        target = await _get_log_target(guild)
        if target and isinstance(target, (discord.TextChannel, discord.Thread)):
            try:
                if not await _modlog_has_recent_ban(guild, user):
                    await target.send(embed=_embed_log_simple(user))
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAutoEmbed(bot))
