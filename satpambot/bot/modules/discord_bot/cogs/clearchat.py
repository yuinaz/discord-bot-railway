import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_LIMIT = 50

class ClearChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.command(name="clearchat", description=f"Hapus pesan di channel ini (default {DEFAULT_LIMIT}).")
    @app_commands.describe(jumlah=f"Jumlah pesan yang dihapus (1-200). Default {DEFAULT_LIMIT}.")
    async def clearchat(self, interaction: discord.Interaction, jumlah: int = DEFAULT_LIMIT):
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = interaction.channel
        limit = max(1, min(200, int(jumlah)))
        deleted = 0

        def check(m: discord.Message) -> bool:
            return not m.pinned

        try:
            deleted = len(await channel.purge(limit=limit, check=check, bulk=True))
        except Exception:
            async for m in channel.history(limit=limit):
                if m.pinned:
                    continue
                try:
                    await m.delete()
                    deleted += 1
                except Exception:
                    pass
        await interaction.followup.send(f"✅ Menghapus {deleted} pesan (pinned dilewati).", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChat(bot))
