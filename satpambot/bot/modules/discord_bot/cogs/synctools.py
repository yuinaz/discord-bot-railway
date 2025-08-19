# synctools.py — shim anti-duplikat; log info kalau slash_sync sudah aktif
import logging
from discord.ext import commands
log = logging.getLogger("slash")
class SyncTools(commands.Cog):
    def __init__(self, bot): self.bot = bot
async def setup(bot):
    # kalau slash_sync sudah terregister, jangan melakukan apa-apa
    if any(ext.endswith('.cogs.slash_sync') for ext in getattr(bot, 'extensions', {}).keys()):
        log.info("[slash] synctools shim tidak dimuat (slash_sync sudah aktif)."); return
    await bot.add_cog(SyncTools(bot))
