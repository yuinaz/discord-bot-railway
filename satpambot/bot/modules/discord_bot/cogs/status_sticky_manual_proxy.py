
from __future__ import annotations
import contextlib
from discord.ext import commands

class StickyManualProxy(commands.Cog):
    """Manual refresh untuk sticky status tanpa bentrok dengan auto cog.
    - Perintah: /status-refresh-manual
    - Jika auto sticky aktif, ini cukup memicu refresh melalui message marker.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="status-refresh-manual", description="Perbarui status sticky secara manual.", with_app_command=True)
    @commands.has_permissions(manage_guild=True)
    async def status_refresh_manual(self, ctx: commands.Context):
        # Coba panggil method dari auto cog jika ada
        cog = self.bot.get_cog("StatusStickyAuto")
        if cog and hasattr(cog, "_upsert"):
            with contextlib.suppress(Exception):
                await cog._upsert(ctx.guild)  # type: ignore
            await ctx.reply("✅ Sticky status diperbarui (auto).", mention_author=False)
            return
        await ctx.reply("ℹ️ Auto sticky tidak aktif; tidak ada yang diperbarui.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(StickyManualProxy(bot))
