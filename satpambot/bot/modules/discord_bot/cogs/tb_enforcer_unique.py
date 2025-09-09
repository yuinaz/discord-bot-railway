from __future__ import annotations

from discord.ext import commands

PREF_NAME = "tb"
PREFERRED_COG = "TBShimFormatted"  # prefer this implementation

class TBEnforcerUnique(commands.Cog):
    """Keep exactly ONE prefix command named 'tb', preferring tb_shim.TBShimFormatted."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ensure_unique(self):
        # Kumpulkan semua command 'tb'
        try:
            tb_cmd = self.bot.get_command(PREF_NAME)  # type: ignore[attr-defined]
        except Exception:
            tb_cmd = None

        # Jika tidak ada atau sudah benar, selesai
        if tb_cmd is None or getattr(getattr(tb_cmd, "cog", None), "__class__", None).__name__ == PREFERRED_COG:
            return

        # Jika bukan dari cog yang diinginkan: un-register lalu biarkan tb_shim mendaftarkan ulang
        try:
            self.bot.remove_command(PREF_NAME)  # type: ignore[attr-defined]
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_unique()


async def setup(bot: commands.Bot):
    await bot.add_cog(TBEnforcerUnique(bot))
