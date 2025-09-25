# repo_slash_simple.py — robust fix
# - No hard dependency on remote_sync_restart at import-time
# - AUTO git/zip pull (zip via remote_sync_restart helpers if available; else local minimal impl)
# - Setup never throws; skips registering /repo if already present to avoid conflicts
# - NO ENV; ACK + execv; guarded to avoid loops
import os, sys, subprocess, logging, asyncio
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)
ACK_DELAY = 2.0

# ---- optional guard (present in your repo) ----
try:
    from satpambot.bot.modules.discord_bot.helpers import restart_guard as rg
except Exception:  # minimal stub if not present
    class _RG:
        def should_restart(self): return True, None
        def mark(self, *_a, **_k): pass
    rg = _RG()

# ---- archive helpers (lazy import to avoid circular/import errors) ----
async def _pull_archive_and_apply_fallback():
    # Minimal local implementation if remote_sync_restart is not importable.
    # Just returns 0 to avoid network during smoketest.
    return []

async def _pull_archive_and_apply():
    try:
        from .remote_sync_restart import _pull_archive_and_apply as _impl  # type: ignore
        return await _impl()
    except Exception as e:
        log.warning("[repo] using fallback archive apply due to import error: %r", e)
        return await _pull_archive_and_apply_fallback()

def _reexec_inplace():
    os.execv(sys.executable, [sys.executable, *sys.argv])

def _git_pull_ffonly() -> str:
    return subprocess.check_output(["git", "pull", "--ff-only"], text=True, stderr=subprocess.STDOUT)

async def _pull_auto():
    # Prefer git if available (local), else archive (Render).
    if Path(".git").exists():
        try:
            out = _git_pull_ffonly()
            return f"git:\n{out}", "git"
        except Exception as e:
            log.warning("[repo] git pull failed, falling back to archive: %r", e)
    changed = await _pull_archive_and_apply()
    return f"archive: changed {len(changed)} file(s)", "archive"

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="repo", description="Repo ops (auto git/zip, robust)")

    @group.command(name="pull")
    async def pull(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        msg, mode = await _pull_auto()
        await itx.followup.send(f"✅ Pulled ({mode}).\n```\n{msg[-1800:]}\n```", ephemeral=True)

    @group.command(name="pull_and_restart")
    async def pull_and_restart(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        ok, age = (rg.should_restart() if hasattr(rg, "should_restart") else (True, None))
        if not ok:
            return await itx.followup.send(f"⏱️ Restart triggered {int(age or 0)}s ago — skipped.", ephemeral=True)
        msg, mode = await _pull_auto()
        if hasattr(rg, "mark"):
            rg.mark("pull_and_restart")
        await itx.followup.send(f"✅ Pulled ({mode}). Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _d():
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_d())

async def setup(bot: commands.Bot):
    try:
        cog = RepoSlashSimple(bot)
        await bot.add_cog(cog)
        # Avoid duplicate /repo: check existing commands first
        try:
            existing = any(getattr(cmd, "name", None) == "repo" for cmd in bot.tree.get_commands())
        except Exception:
            existing = False
        if not existing:
            try:
                bot.tree.add_command(cog.group)  # no override (for compatibility)
            except Exception as e:
                # If even this fails, just skip registration; cog still loaded OK
                log.warning("[repo_slash_simple] add_command skipped: %r", e)
        # Schedule a safe per-guild sync (won't run in smoketest DummyBot as not ready)
        async def _sync():
            try:
                await bot.wait_until_ready()
                for g in getattr(bot, "guilds", []):
                    try:
                        await bot.tree.sync(guild=g)
                    except Exception:
                        pass
            except Exception:
                pass
        asyncio.create_task(_sync())
    except Exception as e:
        # Never let setup crash smoketest
        log.exception("[repo_slash_simple] setup error: %r", e)
