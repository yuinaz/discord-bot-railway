import discord
from discord import app_commands
from discord.ext import commands

class SlashBasic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Cek respons bot (slash command).")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(SlashBasic(bot))
