# satpambot/bot/modules/discord_bot/cogs/a00_disable_auto_update_manager.py
# Non-aktifkan auto_update_manager di build .exe agar tidak memanggil `-m pip` dari EXE.
from discord.ext import commands

TARGET_EXT = "satpambot.bot.modules.discord_bot.cogs.auto_update_manager"

class DisableAutoUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        try:
            # unload jika sudah keburu di-load oleh loader otomatis
            self.bot.unload_extension(TARGET_EXT)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(DisableAutoUpdate(bot))
    # Kalau loader memuat setelah ini, coba unload lagi (idempotent)
    try:
        bot.unload_extension(TARGET_EXT)
    except Exception:
        pass