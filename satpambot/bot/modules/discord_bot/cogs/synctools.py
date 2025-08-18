# synctools.py — shim agar tidak dobel dengan slash_sync.py
import logging
from discord.ext import commands
from .slash_sync import SlashSync  # gunakan implementasi utama

log = logging.getLogger("slash")

async def setup(bot: commands.Bot):
    # Jangan tambah dua kali bila slash_sync sudah diload
    for name in list(getattr(bot, "extensions", {}).keys()):
        if name.endswith(".cogs.slash_sync"):
            log.info("[slash] synctools shim tidak dimuat (slash_sync sudah aktif).")
            return
    await bot.add_cog(SlashSync(bot))
