# repo_slash_simple.py (AUTO: git if exists else archive; NO-ENV; ACK + re-exec)
import os, sys, subprocess, logging, asyncio
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

from .remote_sync_restart import _load_cfg, _pull_archive_and_apply

log = logging.getLogger(__name__)
ACK_DELAY = 2.0  # fixed; no env

def _reexec_inplace():
    py = sys.executable
    os.execv(py, [py, *sys.argv])

def _git_pull_ffonly() -> str:
    return subprocess.check_output(["git", "pull", "--ff-only"], text=True, stderr=subprocess.STDOUT)

async def _pull_auto():
    if Path(".git").exists():
        try:
            out = _git_pull_ffonly()
            return f"git:\n{out}", "git"
        except Exception as e:
            log.warning("[repo] git pull failed: %r; falling back to archive", e)
    cfg = _load_cfg()
    changed = await _pull_archive_and_apply(cfg)
    return f"archive: changed {len(changed)} file(s)", "archive"

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="repo", description="Repo utilities (auto, no-env)")

    @group.command(name="pull", description="Pull (git if available, else archive)")
    async def pull(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        msg, mode = await _pull_auto()
        await itx.followup.send(f"✅ Pulled ({mode}).\n```\n{msg[-1800:]}\n```", ephemeral=True)

    @group.command(name="pull_and_restart", description="Pull + restart (ACK + re-exec)")
    async def pull_and_restart(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        msg, mode = await _pull_auto()
        await itx.followup.send(f"✅ Pulled ({mode}). Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _delay():
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_delay())

async def setup(bot: commands.Bot):
    cog = RepoSlashSimple(bot)
    await bot.add_cog(cog)
    # Register and auto-sync to all guilds, no ENV
    bot.tree.add_command(cog.group, override=True)
    async def _sync():
        await bot.wait_until_ready()
        ids = [g.id for g in bot.guilds]
        for gid in ids:
            try: await bot.tree.sync(guild=discord.Object(id=gid))
            except Exception: pass
    asyncio.create_task(_sync())
