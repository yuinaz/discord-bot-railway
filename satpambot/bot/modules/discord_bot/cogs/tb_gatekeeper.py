from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class TBGatekeeperPreferShim(commands.Cog):
    """Quiet gatekeeper: ensures `tb_shim` is preferred but never spams a user-facing warning.
    This avoids duplicate or scary warnings when some other `tb` exists temporarily on boot.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Only log to console; do not message channels.
        try:
            cmd = getattr(self.bot, "get_command", lambda *_: None)("tb")
            if cmd:
                log.info("[tb_gatekeeper] active prefix command: tb -> %s", cmd.callback.__qualname__)
            else:
                log.warning("[tb_gatekeeper] no 'tb' command registered yet (loader still starting?)")
        except Exception as e:
            log.exception("tb_gatekeeper check failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(TBGatekeeperPreferShim(bot))
