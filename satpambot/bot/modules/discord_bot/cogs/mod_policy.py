# mod_policy.py — fallback policy: jadikan default perms Manage Guild utk command tanpa default_permissions
import logging, discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger("mod_policy")

class ModPolicy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        changed = 0
        for cmd in list(self.bot.tree.get_commands()):
            # Biarkan command yang sudah punya default_permissions sendiri
            if getattr(cmd, 'default_permissions', None):
                continue
            # Jangan sentuh built-in atau DM
            try:
                cmd.default_permissions = app_commands.DefaultPermissions(manage_guild=True)
                changed += 1
            except Exception:
                pass
        if changed:
            try:
                await self.bot.tree.sync()
                log.info("[mod_policy] applied default Manage Guild to %s command(s) and re-synced.", changed)
            except Exception:
                log.exception("[mod_policy] sync failed")

async def setup(bot: commands.Bot):
    await bot.add_cog(ModPolicy(bot))
