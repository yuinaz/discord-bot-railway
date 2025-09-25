
import os, subprocess, logging
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)
GUILD_ID = int(os.getenv("SB_GUILD_ID", "761163966030151701"))

def _commit():
    for k in ("RENDER_GIT_COMMIT","RENDER_GIT_SHA","GIT_COMMIT","SOURCE_VERSION","HEROKU_SLUG_COMMIT","COMMIT_SHA"):
        v = os.getenv(k)
        if v: return v[:7]
    try:
        out = subprocess.check_output(["git","rev-parse","--short","HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        if out: return out
    except Exception: pass
    return "unknown"

class AboutCard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.describe(public="Jika 'True', kirim sebagai pesan publik (default: private/ephemeral)")
    async def about(self, itx: discord.Interaction, public: bool = False):
        # default private (ephemeral)
        ephemeral = not public

        user = self.bot.user
        title = "SatpamBot - Anti Phishing Discord Guard"
        desc = (
            "**Fitur Utama:**\n"
            "🔎 Anti-Phishing (keyword & OCR)\n"
            "⛔ Auto Ban + log ke #mod-command\n"
            "📊 Dashboard monitoring real-time\n"
            "🎨 Ganti tema + upload background\n"
            "📈 Statistik user & server\n"
            "🧩 Plugin Manager & Role Maker\n"
            "🗳️ Polling & perintah admin lainnya"
        )
        embed = discord.Embed(title=title, description=desc, color=0x2f3136)
        if user and user.avatar:
            embed.set_author(name=user.name, icon_url=user.avatar.url)
            embed.set_thumbnail(url=user.avatar.url)
        else:
            embed.set_author(name=user.name if user else "SatpamBot")

        servers = len(self.bot.guilds)
        prefix = os.getenv("BOT_PREFIX", "/")
        creator = os.getenv("BOT_CREATOR", "Tim Developer Satpambot")
        embed.add_field(name="Prefix", value=f"`{prefix}`", inline=True)
        embed.add_field(name="Server Aktif", value=f"`{servers}`", inline=True)
        embed.add_field(name="Creator", value=creator, inline=True)
        embed.set_footer(text=f"Versi commit: {_commit()}")

        try:
            await itx.response.send_message(embed=embed, ephemeral=ephemeral)
        except Exception:
            await itx.followup.send(embed=embed, ephemeral=ephemeral)

    async def cog_load(self):
        guild = discord.Object(id=GUILD_ID)
        # Re-register (guild only)
        try:
            exist = self.bot.tree.get_command("about", guild=guild)
            if exist:
                self.bot.tree.remove_command("about", type=discord.AppCommandType.chat_input, guild=guild)
        except Exception: pass
        cmd = app_commands.Command(name="about", description="Tampilkan kartu info SatpamBot (guild-only).", callback=self.about)
        self.bot.tree.add_command(cmd, guild=guild)
        synced = await self.bot.tree.sync(guild=guild)
        log.info("[about_card] /about registered (ephemeral default) & synced to guild %s (count=%d)", GUILD_ID, len(synced))

async def setup(bot: commands.Bot):
    await bot.add_cog(AboutCard(bot))
