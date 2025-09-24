
import asyncio, json, os, io, zipfile, logging, time, pathlib, sys
from typing import List, Dict, Any
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

CONFIG_SYNC = "config/remote_sync.json"

DEFAULT_REMOTE = {
    "archive": "https://codeload.github.com/yuinaz/discord-bot-railway/zip/refs/heads/main",
    "repo_root_prefix": "discord-bot-railway-main/",
    "pull_sets": [
        {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
        {"include": ["satpambot/"], "allow_exts": ["py","json","txt","yaml","yml"]},
        {"include": [""], "allow_exts": ["py"]}
    ],
    "timeout_s": 25
}

def _load_remote() -> Dict[str, Any]:
    try:
        with open(CONFIG_SYNC, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        out = DEFAULT_REMOTE.copy()
        out.update({k: v for k, v in data.items() if v is not None})
        return out
    except Exception as e:
        log.warning("[repo_slash_simple] cannot read %s: %s; using defaults", CONFIG_SYNC, e)
        return DEFAULT_REMOTE.copy()

def _allowed(rel: str, pull_sets: List[Dict[str, Any]]) -> bool:
    rel_slash = rel.replace("\\", "/")
    if rel_slash.endswith("/"):
        return False
    ext = rel_slash.rsplit(".", 1)[-1].lower() if "." in rel_slash else ""
    for spec in pull_sets:
        includes = [p.replace("\\", "/") for p in spec.get("include", [])]
        allow_exts = [e.lower() for e in spec.get("allow_exts", [])]
        for inc in includes:
            if rel_slash.startswith(inc):
                if not allow_exts or ext in allow_exts:
                    return True
    return False

async def _download(url: str, timeout_s: int) -> bytes:
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                resp.raise_for_status()
                return await resp.read()
    except Exception as e:
        log.warning("[repo_slash_simple] aiohttp download failed (%s); falling back to urllib", e)
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout_s) as r:
            return r.read()

def _apply_zip(data: bytes, repo_root_prefix: str, pull_sets: List[Dict[str, Any]]) -> Dict[str, Any]:
    zf = zipfile.ZipFile(io.BytesIO(data))
    total, written, skipped = 0, 0, 0
    base = repo_root_prefix
    for zi in zf.infolist():
        name = zi.filename
        if not name.startswith(base):
            continue
        rel = name[len(base):]
        if not rel or rel.endswith("/"):
            continue
        total += 1
        if not _allowed(rel, pull_sets):
            skipped += 1
            continue
        target = pathlib.Path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(zi) as src, open(target, "wb") as dst:
            dst.write(src.read())
        written += 1
    return {"total": total, "written": written, "skipped": skipped}

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.group = app_commands.Group(name="repo", description="Repo maintenance (pull & restart)")
        self.group.command(name="pull", description="Pull latest repo archive and apply safe files")(self.pull_cmd)
        self.group.command(name="pull_and_restart", description="Pull then restart process")(self.pull_and_restart_cmd)
        self.group.command(name="restart", description="Restart process only")(self.restart_cmd)
        log.info("[repo_slash_simple] initialized")

    async def cog_load(self):
        try:
            self.bot.tree.add_command(self.group)
            log.info("[repo_slash_simple] group /repo added to tree")
        except Exception as e:
            log.warning("[repo_slash_simple] add_command failed: %s", e)

    async def cog_unload(self):
        try:
            self.bot.tree.remove_command(self.group.name, type=self.group.type)
        except Exception:
            pass

    @app_commands.command(name="pull_and_restart", description="Pull latest archive and restart (alias)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def pull_and_restart_alias(self, itx: discord.Interaction):
        await self._pull_and_restart(itx)

    @app_commands.command(name="repo_pull", description="Pull latest archive and apply (alias)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def repo_pull_alias(self, itx: discord.Interaction):
        await self._pull_only(itx)

    @app_commands.checks.has_permissions(manage_guild=True)
    async def pull_cmd(self, itx: discord.Interaction):
        await self._pull_only(itx)

    @app_commands.checks.has_permissions(manage_guild=True)
    async def pull_and_restart_cmd(self, itx: discord.Interaction):
        await self._pull_and_restart(itx)

    @app_commands.checks.has_permissions(manage_guild=True)
    async def restart_cmd(self, itx: discord.Interaction):
        await itx.response.send_message("Restarting process…", ephemeral=True)
        await itx.followup.send("💤 Exiting now, Render will restart the service.", ephemeral=True)
        await asyncio.sleep(0.8)
        os._exit(0)

    async def _pull_only(self, itx: discord.Interaction):
        await itx.response.send_message("⬇️ Downloading and applying latest archive…", ephemeral=True)
        r = _load_remote()
        data = await _download(r["archive"], int(r.get("timeout_s", 20)))
        stats = _apply_zip(data, r["repo_root_prefix"], r["pull_sets"])
        await itx.followup.send(f"✅ Pulled. Files total={stats['total']}, applied={stats['written']}, skipped={stats['skipped']}.", ephemeral=True)

    async def _pull_and_restart(self, itx: discord.Interaction):
        await itx.response.send_message("⬇️ Downloading and applying latest archive, then restarting…", ephemeral=True)
        r = _load_remote()
        data = await _download(r["archive"], int(r.get("timeout_s", 20)))
        stats = _apply_zip(data, r["repo_root_prefix"], r["pull_sets"])
        await itx.followup.send(f"✅ Pulled (applied={stats['written']}, skipped={stats['skipped']}). Restarting…", ephemeral=True)
        await asyncio.sleep(0.8)
        os._exit(0)

async def setup(bot: commands.Bot):
    await bot.add_cog(RepoSlashSimple(bot))
