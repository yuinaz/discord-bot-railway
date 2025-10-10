
import os
import re
import asyncio
import logging
from discord.ext import commands
import discord

LOG = logging.getLogger(__name__)

def _get_focus_id() -> int:
    raw = os.getenv("LOG_CHANNEL_ID") or ""
    try:
        return int(raw)
    except Exception:
        return 0

class AutoCleanLogChannel(commands.Cog):
    """Auto-delete bot messages in log channel, except pinned/keepers."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.focus_id = _get_focus_id()
        # default TTL 3 minutes
        self.ttl = int(os.getenv("LOG_AUTO_DELETE_TTL", "180"))
        # Messages containing any of these markers will NEVER be deleted
        self._exempt_re = re.compile(
            r"(SATPAMBOT_(?:STATUS|PHASH)_V1|NEURO[- ]LITE|PHASH_DB|keeper|memory\s+keeper)",
            re.I
        )

    def _is_exempt(self, msg: discord.Message) -> bool:
        if not msg:
            return True
        if not msg.channel or msg.channel.id != self.focus_id:
            return True
        if msg.pinned:
            return True
        # Only auto-delete bot-authored messages to be safe
        if self.bot.user and msg.author.id != self.bot.user.id:
            return True
        # If it looks like a keeper/status message, protect it
        if msg.content and self._exempt_re.search(msg.content or ""):
            return True
        for e in (msg.embeds or []):
            title = f"{e.title or ''} {e.description or ''}"
            if self._exempt_re.search(title):
                return True
        return False

    async def _cleanup_later(self, msg: discord.Message):
        if self._is_exempt(msg):
            return
        try:
            await asyncio.sleep(self.ttl)
            # re-fetch to see if it's pinned later
            try:
                fresh = await msg.channel.fetch_message(msg.id)
                if fresh.pinned:
                    return
            except Exception:
                pass
            await msg.delete()
        except discord.Forbidden:
            # ignore quietly
            return
        except Exception:
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.focus_id or message.channel.id != self.focus_id:
            return
        # schedule in background
        asyncio.create_task(self._cleanup_later(message))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not self.focus_id or after.channel.id != self.focus_id:
            return
        asyncio.create_task(self._cleanup_later(after))

def setup(bot):
    try:
        bot.add_cog(AutoCleanLogChannel(bot))
        LOG.info("[log_autodelete_focus] ready (ttl=%ss)", int(os.getenv("LOG_AUTO_DELETE_TTL", "180")))
    except Exception as e:
        LOG.error("[log_autodelete_focus] failed to add cog: %s", e)
