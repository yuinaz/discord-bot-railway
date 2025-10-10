# a00_disable_auto_update_manager.py
from discord.ext import commands
TARGET_EXT = "satpambot.bot.modules.discord_bot.cogs.auto_update_manager"
class DisableAutoUpdate(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        try: self.bot.unload_extension(TARGET_EXT)
        except Exception: pass
async def setup(bot):
    await bot.add_cog(DisableAutoUpdate(bot))
    try: bot.unload_extension(TARGET_EXT)
    except Exception: pass
