from __future__ import annotations
import re, logging
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from ..helpers.log_utils import find_text_channel

log = logging.getLogger(__name__)

URL_RX = re.compile(r"https?://[^\s>]+", re.I)
LOOKALIKE = {
    "dlscord.com","discord-gift.com","discordnitro","discorcl.com","dlscordapp",
    "steancommunity.com","steamcommunitiy","steampowered-gifts","stearn",
    "dlscordapp.com","discorcl-app.com"
}
TLD_BAD = {".ru",".cn",".xyz",".top",".gq",".tk",".ml",".cf",".click",".icu",".zip",".mov"}

def _suspect(u: str) -> bool:
    u = u.lower()
    if "xn--" in u: return True
    if any(u.endswith(t) for t in TLD_BAD): return True
    host = u.split("/")[2] if "://" in u else u
    for bad in LOOKALIKE:
        if bad in host:
            return True
    return False

class LinkGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or getattr(message.author, "bot", False):
                return
            text = getattr(message, "content", "") or ""
            urls = URL_RX.findall(text)
            urls = urls or []
            bads = [u for u in urls if _suspect(u)]
            if not bads:
                return

            timed_out = False
            try:
                until = datetime.now(timezone.utc) + timedelta(minutes=int((__import__('os').getenv('LINK_GUARD_TIMEOUT_MINUTES') or '10')))
                if isinstance(message.author, discord.Member):
                    await message.author.edit(timeout=until, reason="LinkGuard: lookalike/phish tld")
                    timed_out = True
            except Exception:
                pass

            try:
                await delete_message_safe(message, actor="LinkGuard")
            except Exception:
                pass

            try:
                ch = await find_text_channel(self.bot, name="log-botphising")
                if ch:
                    act = "timeout+delete" if timed_out else "delete"
                    await ch.send(f"🧨 [LinkGuard] {act} {message.author.mention} in {message.channel.mention} — {', '.join(bads[:3])}")
            except Exception:
                pass
        except Exception:
            log.debug("LinkGuard error", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(LinkGuard(bot))
