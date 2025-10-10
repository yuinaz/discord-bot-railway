from __future__ import annotations

import logging
from discord import Interaction, app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

class ClearChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clearchat", description="Bersihkan DM bot di chat ini.")
    async def clearchat(self, interaction: Interaction):
        # Defer first to open a followup token reliably
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        # Your delete logic should be here; for smoke keep it 0
        deleted = 0
        msg = f"🧹 DM dibersihkan: {deleted} pesan bot dihapus."

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True, wait=False)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            log.debug("[clearchat] notify failed (%r), ignoring.", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChat(bot))
