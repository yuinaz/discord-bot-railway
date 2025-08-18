import discord
from discord import app_commands
from discord.ext import commands

MAX_LIMIT = 1000

# Dibuat dengan gaya yang sama seperti command /tb: module-level app_commands.command,
# lalu ditambahkan ke tree pada setup().

@app_commands.command(name="clearchat", description="Bersihkan sejumlah pesan dari channel ini.")
@app_commands.describe(jumlah=f"Jumlah pesan yang dihapus (1–{MAX_LIMIT})")
@app_commands.guild_only()
async def clearchat(interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, MAX_LIMIT] = 50):
    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        return await interaction.response.send_message("Perintah ini hanya untuk teks channel.", ephemeral=True)

    # Cek izin runtime (agar command tetap terlihat seperti /tb, tapi aman saat dieksekusi)
    perms = channel.permissions_for(interaction.user)
    if not perms.manage_messages:
        return await interaction.response.send_message(
            "❌ Kamu perlu **Manage Messages** di channel ini untuk menjalankan /clearchat.",
            ephemeral=True,
        )

    await interaction.response.defer(ephemeral=True, thinking=True)
    deleted = await channel.purge(limit=jumlah, reason=f"/clearchat by {interaction.user}")
    await interaction.followup.send(f"✅ {len(deleted)} pesan dibersihkan.", ephemeral=True)

async def setup(bot: commands.Bot):
    # Tambahkan command ke tree seperti /tb biasanya dilakukan
    bot.tree.add_command(clearchat)
