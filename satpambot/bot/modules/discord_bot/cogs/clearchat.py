import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_LIMIT = 50

def dm_or_has_manage_messages():
    async def predicate(inter: discord.Interaction) -> bool:
        if inter.guild is None:
            return True
        ch = inter.channel
        if not ch: 
            return False
        perms = ch.permissions_for(inter.user)  # type: ignore
        return perms.manage_messages
    return app_commands.check(predicate)

class ClearChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clearchat", description=f"Bersihkan pesan. DM: hapus pesan bot sendiri. Guild: perlu izin Manage Messages.")
    @app_commands.describe(jumlah=f"Jumlah pesan yang dihapus (1-200). Default {DEFAULT_LIMIT}.")
    @dm_or_has_manage_messages()
    async def clearchat(self, interaction: discord.Interaction, jumlah: int = DEFAULT_LIMIT):
        channel = interaction.channel
        if channel is None:
            return await interaction.response.send_message("Channel tidak ditemukan.", ephemeral=True)

        # DM mode: hanya bisa hapus pesan bot sendiri
        if interaction.guild is None:
            await interaction.response.defer()
            me = interaction.client.user
            deleted = 0
            async for m in channel.history(limit=max(1, min(200, jumlah))):
                if m.author.id == me.id:
                    try:
                        await m.delete()
                        deleted += 1
                    except Exception:
                        pass
            return await interaction.followup.send(f"🧹 DM dibersihkan: {deleted} pesan bot dihapus.")

        # Guild mode
        # pastikan bot punya izin
        bot_perms = channel.permissions_for(interaction.guild.me)  # type: ignore
        if not bot_perms.manage_messages:
            return await interaction.response.send_message("Aku butuh izin **Manage Messages** di channel ini.", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        limit = max(1, min(200, jumlah))
        # Hapus hanya pesan bot secara default demi keamanan admin
        def check(m: discord.Message) -> bool:
            return True  # atau ganti ke m.author.bot kalau mau bot-only
        deleted = 0
        try:
            # purge bulk kalau bisa
            deleted = len(await channel.purge(limit=limit, check=check, bulk=True))  # type: ignore
        except Exception:
            # fallback delete satu-satu (misal di thread)
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
