
from __future__ import annotations
import asyncio, json, os, io, zipfile
from pathlib import Path
from typing import List, Dict, Any
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

CFG_PATH = Path("config") / "remote_sync.json"
DEFAULT_CFG = {
    "base": "", "archive": "", "repo_root_prefix": "",
    "pull_sets": [
        {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
        {"include": ["satpambot/bot/modules/discord_bot/cogs/"], "allow_exts": ["py"]},
        {"include": ["satpambot/bot/modules/discord_bot/helpers/"], "allow_exts": ["py"]},
        {"include": [""], "allow_exts": ["py"]}
    ],
    "files": [], "timeout_s": 20
}

def _load_cfg() -> Dict[str, Any]:
    try:
        return {**DEFAULT_CFG, **json.loads(Path(CFG_PATH).read_text("utf-8"))}
    except Exception:
        return dict(DEFAULT_CFG)

async def _fetch_bytes(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> bytes:
    async with session.get(url, timeout=timeout) as r:
        r.raise_for_status(); return await r.read()

def _should_include(path: str, cfg: Dict[str, Any]) -> bool:
    for rule in cfg.get("pull_sets", []):
        if any(path.startswith(prefix) for prefix in rule.get("include", [])):
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            return (ext in (rule.get("allow_exts") or [])) if rule.get("allow_exts") else True
    return False

async def _apply_archive_bytes(data: bytes, cfg: Dict[str, Any]) -> List[str]:
    changed: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        root = (cfg.get("repo_root_prefix") or "").strip()
        for n in zf.namelist():
            if root and not n.startswith(root): continue
            rel = n[len(root):] if root else n
            if not _should_include(rel, cfg): continue
            try:
                b = zf.read(n)
                os.makedirs(os.path.dirname(rel) or ".", exist_ok=True)
                old = None
                try:
                    with open(rel, "rb") as f: old = f.read()
                except Exception:
                    pass
                if old != b:
                    with open(rel, "wb") as f: f.write(b)
                    changed.append(rel)
            except Exception:
                pass
    return changed

async def _pull_archive_and_apply(cfg: Dict[str, Any]) -> List[str]:
    url = cfg.get("archive")
    if not url: return []
    timeout = int(cfg.get("timeout_s", 20))
    async with aiohttp.ClientSession() as s:
        data = await _fetch_bytes(s, url, timeout)
        return await _apply_archive_bytes(data, cfg)

async def _pull_all_raw(cfg: Dict[str, Any]) -> List[str]:
    base = (cfg.get("base") or "").rstrip("/") + "/"
    files = cfg.get("files") or []
    changed: List[str] = []
    timeout = int(cfg.get("timeout_s", 20))
    if not files: return []
    async with aiohttp.ClientSession() as s:
        for row in files:
            try:
                remote = row.get("remote"); local = row.get("local")
                if not remote or not local: continue
                url = base + remote
                data = await _fetch_bytes(s, url, timeout)
                os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
                old = None
                try:
                    with open(local, "rb") as f: old = f.read()
                except Exception:
                    pass
                if old != data:
                    with open(local, "wb") as f: f.write(data)
                    changed.append(local)
            except Exception:
                pass
    return changed

class RemoteSyncRestart(commands.Cog):
    def __init__(self, bot): self.bot = bot

    group = app_commands.Group(name="repo", description="Remote pull & restart (Render-friendly)")
    group_rt = app_commands.Group(name="runtime", description="Runtime ops")

    @group.command(name="pull")
    async def pull(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.defer(ephemeral=True, thinking=True)
        cfg = _load_cfg()
        try: changed = await _pull_archive_and_apply(cfg)
        except Exception as e: return await itx.followup.send(f"Gagal pull: `{e}`", ephemeral=True)
        await itx.followup.send(f"Selesai. File yang berubah: {changed}", ephemeral=True)

    @group.command(name="pull_and_restart")
    async def pull_and_restart(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.defer(ephemeral=True, thinking=True)
        cfg = _load_cfg()
        try: changed = await _pull_archive_and_apply(cfg)
        except Exception as e: return await itx.followup.send(f"Gagal pull: `{e}`", ephemeral=True)
        await itx.followup.send(f"Berubah: {changed}. Restarting…", ephemeral=True)
        await asyncio.sleep(2.0); os._exit(0)

    @group_rt.command(name="restart")
    async def rt_restart(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.send_message("Restarting dalam 2 detik…", ephemeral=True)
        await asyncio.sleep(2.0); os._exit(0)

async def setup(bot: commands.Bot):
    await bot.add_cog(RemoteSyncRestart(bot))
