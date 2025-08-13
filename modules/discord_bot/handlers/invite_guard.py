\
import re, os, discord

INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.IGNORECASE)
NSFW_WORDS = {"nsfw","18+","hentai","porn","xxx","sex","lewd","r18","🔞","onlyfans","boobs","nude","nudity","erotic"}

BAN_DELETE_MESSAGE_DAYS = 7
OWN_GUILD_WHITELIST = {int(x) for x in os.getenv('OWN_GUILD_WHITELIST','').split(',') if x.isdigit()}

def _looks_nsfw_text(s: str) -> bool:
    s = (s or "").lower()
    return any(k in s for k in NSFW_WORDS)

async def check_nsfw_invites(message: discord.Message, bot):
    if not message or message.author.bot:
        return
    m = INVITE_RE.search(message.content or "")
    if not m:
        return
    code = m.group(1)

    invite = None
    try:
        invite = await bot.fetch_invite(code, with_counts=False, with_expiration=False)
    except Exception:
        pass

    is_nsfw = False
    channel = getattr(invite, "channel", None) if invite else None
    guild = getattr(invite, "guild", None) if invite else None

    if guild and getattr(guild, "id", None) in OWN_GUILD_WHITELIST:
        return

    try:
        if channel and hasattr(channel, "nsfw") and channel.nsfw:
            is_nsfw = True
    except Exception:
        pass

    try:
        nsfw_level = getattr(guild, "nsfw_level", None)
        if nsfw_level is not None:
            val = int(getattr(nsfw_level, "value", nsfw_level))
            if val >= 2:
                is_nsfw = True
        elif str(nsfw_level).lower() in {"explicit","age_restricted"}:
            is_nsfw = True
    except Exception:
        pass

    try:
        texts = []
        if guild: texts += [getattr(guild, "name", "") or "", getattr(guild, "description", "") or ""]
        if channel: texts += [getattr(channel, "name", "") or "", getattr(channel, "topic", "") or ""]
        if _looks_nsfw_text(" ".join(texts)):
            is_nsfw = True
    except Exception:
        pass

    if not is_nsfw:
        return

    # Delete + Ban (max level)
    try:
        if message.guild and message.guild.me and message.guild.me.guild_permissions.manage_messages:
            try: await message.delete()
            except Exception: pass
    except Exception:
        pass

    try:
        if message.guild and message.guild.me and message.guild.me.guild_permissions.ban_members:
            await message.guild.ban(message.author, delete_message_days=BAN_DELETE_MESSAGE_DAYS, reason="Posting NSFW Discord invite (auto)")
            return
    except Exception:
        pass

    # fallback: timeout 7 days
    try:
        if message.guild and message.guild.me and message.guild.me.guild_permissions.moderate_members:
            duration = discord.utils.utcnow() + discord.timedelta(days=7)
            await message.author.edit(timeout=duration, reason="Posting NSFW Discord invite (auto)")
    except Exception:
        pass
