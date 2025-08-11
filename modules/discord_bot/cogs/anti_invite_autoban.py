import re
from discord.ext import commands
import discord

INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.IGNORECASE)

NSFW_KEYWORDS = {
    "nsfw","18+","18 ++","18plus","hentai","porn","xxx","sex","lewd","r18","🔞",
    "🍑","🍆","💦","onlyfans","boobs","nude","nudity","erotic","fetish","bdsm","camgirl","camsex",
}

def looks_nsfw_text(s: str) -> bool:
    if not s:
        return False
    s = s.lower()
    for kw in NSFW_KEYWORDS:
        if kw in s:
            return True
    return False

BAN_DELETE_MESSAGE_DAYS = 7  # maximum cleanup
GUILD_ID_WHITELIST = set()   # e.g., {123456789012345678}

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or message.author.bot:
            return
        content = message.content or ""
        m = INVITE_RE.search(content)
        if not m:
            return

        code = m.group(1)

        # Try to fetch invite to check NSFW; if cannot fetch, use heuristics later
        invite = None
        try:
            invite = await self.bot.fetch_invite(code, with_counts=False, with_expiration=False)
        except Exception:
            pass

        is_nsfw = False
        channel = getattr(invite, "channel", None) if invite else None
        guild = getattr(invite, "guild", None) if invite else None

        if guild and getattr(guild, "id", None) in GUILD_ID_WHITELIST:
            return

        # API-based checks
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
            elif str(nsfw_level).lower() in {"explicit", "age_restricted"}:
                is_nsfw = True
        except Exception:
            pass

        # Heuristic fallback
        try:
            texts = []
            if guild:
                texts.append(getattr(guild, "name", "") or "")
                texts.append(getattr(guild, "description", "") or "")
            if channel:
                texts.append(getattr(channel, "name", "") or "")
                texts.append(getattr(channel, "topic", "") or "")
            combined = " ".join([t for t in texts if t])
            if looks_nsfw_text(combined):
                is_nsfw = True
        except Exception:
            pass

        if not is_nsfw:
            return  # allow non-NSFW invites

        # Act: delete message and ban author (maximum severity)
        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.manage_messages:
                try:
                    await message.delete()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.ban_members:
                await message.guild.ban(
                    message.author,
                    delete_message_days=BAN_DELETE_MESSAGE_DAYS,
                    reason="Posting NSFW Discord invite (auto)"
                )
                return
        except Exception:
            pass

        # Fallback: timeout if cannot ban
        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.moderate_members:
                duration = discord.utils.utcnow() + discord.timedelta(days=7)
                await message.author.edit(timeout=duration, reason="Posting NSFW Discord invite (auto)")
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiInviteAutoban(bot))
