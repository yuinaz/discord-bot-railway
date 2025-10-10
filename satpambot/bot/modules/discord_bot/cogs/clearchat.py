import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

class ClearChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clearchat", description="Bersihkan DM dari pesan bot ini")
    async def clearchat(self, interaction: discord.Interaction):
        # respon cepat agar token valid
        try:
            await interaction.response.defer(ephemeral=True, thinking=False)
        except Exception:
            pass

        deleted = 0
        try:
            user = interaction.user
            dm: Optional[discord.DMChannel] = user.dm_channel or await user.create_dm()
            async for m in dm.history(limit=200):
                if m.author.id == self.bot.user.id:
                    try:
                        await m.delete()
                        deleted += 1
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        # tidak punya izin hapus DM (harusnya boleh), hentikan
                        break
        except Exception:
            log.exception("[clearchat] gagal scan DM")

        # kirim hasil
        msg = f"🧹 DM dibersihkan: {deleted} pesan bot dihapus."
        try:
            await interaction.followup.send(msg, ephemeral=True)
        except discord.NotFound:
            # fallback: kirim DM balik
            try:
                await interaction.user.send(msg)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChat(bot))
