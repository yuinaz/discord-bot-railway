from discord.ext import commands
import discord
from discord import app_commands

MAX_LIMIT = 1000
@app_commands.command(name="clearchat", description="Bersihkan sejumlah pesan dari channel ini.")
@app_commands.describe(jumlah=f"Jumlah pesan yang dihapus (1–{MAX_LIMIT})")
@app_commands.guild_only()
async def clearchat(interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, MAX_LIMIT] = 50):
    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("Perintah ini hanya untuk teks channel.", ephemeral=True)
    perms = channel.permissions_for(interaction.user)
    if not perms.manage_messages:
        return await interaction.response.send_message("❌ Kamu perlu **Manage Messages** di channel ini untuk menjalankan /clearchat.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    deleted = await channel.purge(limit=jumlah, reason=f"/clearchat by {interaction.user}")
    await interaction.followup.send(f"✅ {len(deleted)} pesan dibersihkan.", ephemeral=True)
async def setup(bot: commands.Bot): bot.tree.add_command(clearchat)