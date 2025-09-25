
import os, sys, subprocess, logging, asyncio
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from satpambot.bot.modules.discord_bot.helpers import restart_guard as rg

log = logging.getLogger(__name__)

def _reexec_inplace():
    py = sys.executable
    os.execv(py, [py, *sys.argv])

def _git_pull_ffonly() -> str:
    out = subprocess.check_output(["git", "pull", "--ff-only"], text=True, stderr=subprocess.STDOUT)
    return out

ACK_DELAY = float(os.getenv("SB_RESTART_ACK_DELAY_SEC", "2.0"))

async def _delayed_reexec():
    try:
        await asyncio.sleep(ACK_DELAY)
    except Exception:
        pass
    _reexec_inplace()

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="repo", description="Repo utilities (guild-only)")

    @group.command(name="pull", description="Pull latest (filtered) dan apply safe files")
    async def repo_pull(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        out = _git_pull_ffonly()
        await itx.followup.send(f"✅ Pulled.\n```\n{out[-1800:]}\n```", ephemeral=True)

    @group.command(name="restart", description="Restart process (debounce, re-exec setelah ack)")
    async def restart(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        ok, age = rg.should_restart()
        if not ok:
            await itx.followup.send(f"⏱️ Restart sudah dipicu {int(age)}s lalu — di-skip.", ephemeral=True)
            return
        rg.mark("manual_restart")
        await itx.followup.send(f"🔁 Restarting in {ACK_DELAY:.1f}s… (in-process re-exec)", ephemeral=True)
        # Penting: jadwalkan re-exec sesudah ack terkirim
        asyncio.create_task(_delayed_reexec())

    @group.command(name="pull_and_restart", description="Pull lalu restart (debounce, re-exec setelah ack)")
    async def pull_and_restart(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        ok, age = rg.should_restart()
        if not ok:
            await itx.followup.send(f"⏱️ Restart sudah dipicu {int(age)}s lalu — di-skip.", ephemeral=True)
            return
        out = _git_pull_ffonly()
        rg.mark("pull_and_restart")
        await itx.followup.send(f"✅ Pulled ({len(out)} chars). Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        asyncio.create_task(_delayed_reexec())

    @group.command(name="guard_clear", description="Hapus lock restart (kalau perlu)")
    async def guard_clear(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        rg.clear()
        await itx.followup.send("🧹 Cleared restart guard.", ephemeral=True)

async def setup(bot: commands.Bot):
    gid = os.getenv("SB_GUILD_ID")
    cog = RepoSlashSimple(bot)
    await bot.add_cog(cog)
    try:
        if gid:
            guild = discord.Object(id=int(gid))
            bot.tree.add_command(cog.group, guild=guild, override=True)
            synced = await bot.tree.sync(guild=guild)
            log.info("[repo_slash_simple] guild-only registered & synced to %s (count=%d)", gid, len(synced))
        else:
            bot.tree.add_command(cog.group, override=True)
            synced = await bot.tree.sync()
            log.info("[repo_slash_simple] global registered & synced (count=%d)", len(synced))
    except Exception as e:
        log.warning("[repo_slash_simple] sync warn: %r", e)
