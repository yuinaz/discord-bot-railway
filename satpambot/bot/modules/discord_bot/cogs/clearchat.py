import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_LIMIT = 50
MAX_LIMIT = 1000

class ClearChat(commands.Cog):
    """Hapus sejumlah pesan di channel saat ini (slash + prefix)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clearchat", description=f"Hapus pesan di channel ini (default {DEFAULT_LIMIT}).")
    @app_commands.describe(jumlah=f"Jumlah pesan yang dihapus (1–{MAX_LIMIT})")
    @app_commands.default_permissions(manage_guild=True)  # agar moderator bisa MELIHAT command
    @app_commands.guild_only()
    async def clearchat(self, interaction: discord.Interaction, jumlah: int = DEFAULT_LIMIT):
        # Validasi izin runtime: butuh Manage Messages di channel ini
        perms = interaction.channel.permissions_for(interaction.user)
        if not perms.manage_messages:
            return await interaction.response.send_message(
                "❌ Kamu perlu **Manage Messages** di channel ini untuk menjalankan /clearchat.",
                ephemeral=True,
            )
        jumlah = max(1, min(jumlah, MAX_LIMIT))
        await interaction.response.defer(ephemeral=True, thinking=True)
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return await interaction.followup.send("Perintah ini hanya untuk teks channel.", ephemeral=True)
        deleted = await channel.purge(limit=jumlah, reason=f"/clearchat by {interaction.user}")
        await interaction.followup.send(f"✅ {len(deleted)} pesan dibersihkan.", ephemeral=True)

    @commands.command(name="clear", help=f"Hapus pesan (1–{MAX_LIMIT}), default {DEFAULT_LIMIT}")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear_prefix(self, ctx: commands.Context, jumlah: int = DEFAULT_LIMIT):
        jumlah = max(1, min(jumlah, MAX_LIMIT))
        deleted = await ctx.channel.purge(limit=jumlah, reason=f"!clear by {ctx.author}")
        try:
            await ctx.reply(f"✅ {len(deleted)} pesan dibersihkan.", delete_after=5)
        except discord.Forbidden:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChat(bot))
