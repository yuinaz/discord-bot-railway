
import os, time, json, subprocess, logging, pathlib
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)
PROCESS_START = time.time()
GUILD_ID = int(os.getenv("SB_GUILD_ID", "761163966030151701"))

def _uptime():
    s = int(time.time() - PROCESS_START)
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h}h {m}m {s}s"

def _commit():
    for key in ("RENDER_GIT_COMMIT","RENDER_GIT_SHA","GIT_COMMIT","SOURCE_VERSION","HEROKU_SLUG_COMMIT","COMMIT_SHA"):
        v = os.getenv(key)
        if v: return v[:7]
    try:
        out = subprocess.check_output(["git","rev-parse","--short","HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        if out: return out
    except Exception: pass
    p = pathlib.Path(".commit")
    if p.exists():
        try:
            t = p.read_text().strip()
            if t: return t[:7]
        except Exception: pass
    return "unknown"

def _remote_cfg():
    try:
        with open("config/remote_sync.json","r",encoding="utf-8") as f:
            j = json.load(f) or {}
        return j.get("archive") or "-", j.get("repo_root_prefix") or "-"
    except Exception: return "-", "-"

class StatusCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.describe(public="Jika 'True', kirim sebagai pesan publik (default: private/ephemeral)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def status(self, itx: discord.Interaction, public: bool = False):
        # default private (ephemeral)
        ephemeral = not public
        try:
            await itx.response.defer(ephemeral=ephemeral, thinking=True)
        except Exception: pass

        arc, pref = _remote_cfg()
        lines = [
            f"**Bot:** {self.bot.user} (`{self.bot.user.id}`)" if self.bot.user else "**Bot:** (unknown)",
            f"**Uptime:** {_uptime()}",
            f"**Commit:** `{_commit()}`",
            f"**Web Port:** `{os.getenv('PORT','10000')}`",
            f"**Remote Archive:** `{arc}`",
            f"**Repo Prefix:** `{pref}`",
            f"**Guild:** `{itx.guild.id if itx.guild else 'DM'}`",
        ]
        msg = "📊 **Status**\n" + "\n".join("• " + s for s in lines)
        await itx.followup.send(msg, ephemeral=ephemeral)

    async def cog_load(self):
        guild = discord.Object(id=GUILD_ID)
        # Re-register (guild only)
        try:
            exist = self.bot.tree.get_command("status", guild=guild)
            if exist:
                self.bot.tree.remove_command("status", type=discord.AppCommandType.chat_input, guild=guild)
        except Exception: pass
        cmd = app_commands.Command(name="status", description="Cek status bot & repo (guild-only).", callback=self.status)
        self.bot.tree.add_command(cmd, guild=guild)
        synced = await self.bot.tree.sync(guild=guild)
        log.info("[status_check] /status registered (ephemeral default) & synced to guild %s (count=%d)", GUILD_ID, len(synced))

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCheck(bot))
