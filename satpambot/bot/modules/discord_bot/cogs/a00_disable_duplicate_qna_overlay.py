from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
TARGETS = [
    "satpambot.bot.modules.discord_bot.cogs.a24_autolearn_qna_autoreply",
]
class DisableDuplicateQnaOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        # if both a06 and a24 cogs are present, attempt to unload a24 module
        try:
            for name in list(self.bot.cogs.keys()):
                if "Auto" in name and "Qna" in name:
                    # leave one; if there are more than one, try unload target module by extension
                    pass
            for m in TARGETS:
                try:
                    await self.bot.unload_extension(m)
                    log.warning("[qna-dup] unloaded %s to avoid duplicate auto-answer", m)
                except Exception: pass
        except Exception as e:
            log.debug("[qna-dup] no-op: %r", e)
async def setup(bot): await bot.add_cog(DisableDuplicateQnaOverlay(bot))