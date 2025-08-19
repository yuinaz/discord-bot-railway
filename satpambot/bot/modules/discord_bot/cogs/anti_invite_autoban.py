from __future__ import annotations
import logging, re
from discord.ext import commands
import discord

log = logging.getLogger(__name__)
INVITE_RE = re.compile(r"(discord\.gg/\w+|discord\.com/invite/\w+)", re.I)

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Placeholder: Only detect pattern; no autoban here
        if message.author.bot:
            return
        if INVITE_RE.search(message.content or ""):
            # Just log for now
            log.debug("[invite] detected invite in #%s", getattr(message.channel, "name", "?"))

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiInviteAutoban(bot))
