from __future__ import annotations
import re, logging
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from satpambot.bot.modules.discord_bot.helpers.log_utils import find_text_channel

log = logging.getLogger(__name__)

INVITE_RE = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.I)

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or getattr(message.author, "bot", False):
                return
            text = getattr(message, "content", "") or ""
            m = INVITE_RE.search(text)
            if not m:
                return
            # If invite not to this guild, delete (autoban optional: off by default)
            try:
                await delete_message_safe(message, actor="InviteGuard")
            except Exception:
                pass
            try:
                ch = await find_text_channel(self.bot, name="log-botphising")
                if ch:
                    await ch.send(f"🚫 [InviteGuard] Deleted external invite by {message.author.mention} in {message.channel.mention}")
            except Exception:
                pass
        except Exception:
            log.debug("AntiInvite handler error", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiInviteAutoban(bot))
