import re
from discord.ext import commands
import discord

INVITE_RE = re.compile(r"(?:https?://)?(?:discord\.gg/|discord\.com/invite/)([A-Za-z0-9-]+)", re.IGNORECASE)

# Behavior: ONLY act (delete+ban) when invite is NSFW.
# Non‑NSFW invites are ignored (not deleted, not punished).
# Optional: allow invites to specific guild IDs even if NSFW (keep default empty).
GUILD_ID_WHITELIST = set()  # e.g., {123456789012345678}

BAN_DELETE_MESSAGE_DAYS = 1  # 0-7, only applied when banning for NSFW invite

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot/self messages
        if not message or message.author.bot:
            return
        content = message.content or ""
        m = INVITE_RE.search(content)
        if not m:
            return

        code = m.group(1)

        # Try to fetch invite to check NSFW; if cannot fetch, do nothing
        try:
            invite = await self.bot.fetch_invite(code, with_counts=False, with_expiration=False)
        except Exception:
            return  # fail‑safe: don't punish if unsure

        # Determine NSFW
        is_nsfw = False

        # Some invites link to a channel
        try:
            channel = invite.channel
        except Exception:
            channel = None

        if channel and hasattr(channel, "nsfw"):
            try:
                if channel.nsfw:
                    is_nsfw = True
            except Exception:
                pass

        # Guild-level NSFW (explicit) if available
        guild = getattr(invite, "guild", None)
        if guild:
            # Skip action if guild is whitelisted
            if getattr(guild, "id", None) in GUILD_ID_WHITELIST:
                return
            nsfw_level = getattr(guild, "nsfw_level", None)
            # discord.NSFWLevel.explicit == 2 typically; fall back to str check
            if nsfw_level is not None:
                try:
                    # support enum or plain int
                    val = int(getattr(nsfw_level, "value", nsfw_level))
                    if val >= 2:
                        is_nsfw = True
                except Exception:
                    # string comparisons as fallback
                    if str(nsfw_level).lower() in {"explicit", "age_restricted"}:
                        is_nsfw = True

        # If NOT NSFW -> allow invite (do nothing)
        if not is_nsfw:
            return

        # NSFW: delete message (if possible) and ban author
        # Only act if we have permissions
        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.manage_messages:
                try:
                    await message.delete()
                except Exception:
                    pass
        except Exception:
            pass

        # Ban user for posting NSFW invite
        try:
            if message.guild and message.guild.me and message.guild.me.guild_permissions.ban_members:
                await message.guild.ban(
                    message.author,
                    delete_message_days=BAN_DELETE_MESSAGE_DAYS,
                    reason="Posting NSFW Discord invite"
                )
        except Exception:
            # As a fallback, try timeout if banning not permitted
            try:
                if message.guild and message.guild.me and message.guild.me.guild_permissions.moderate_members:
                    # 1 day timeout as fallback
                    duration = discord.utils.utcnow() + discord.timedelta(days=1)
                    await message.author.edit(timeout=duration, reason="Posting NSFW Discord invite")
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiInviteAutoban(bot))
