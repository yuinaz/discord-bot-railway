# remote_sync_restart.py (NO-ENV, guild auto-sync, archive ZIP friendly)
from __future__ import annotations
import asyncio, json, os, sys, io, zipfile, logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

log = logging.getLogger(__name__)

# ---------- Archive pull helpers (Render-friendly) ----------

async def _fetch_bytes(s: aiohttp.ClientSession, url: str, timeout: int) -> bytes:
    async with s.get(url, timeout=timeout) as r:
        r.raise_for_status()
        return await r.read()

def _should_include(name: str, cfg: Dict[str, Any]) -> bool:
    # Honor allowlists from config/remote_sync.json
    pulls = cfg.get("pull_sets") or []
    name_l = name.lower()
    for rule in pulls:
        inc = rule.get("include") or []
        exts = rule.get("allow_exts") or []
        if inc and not any(name.startswith(i) for i in inc):
            continue
        if exts and not any(name_l.endswith("."+e.lower()) for e in exts):
            continue
        return True
    return False

def _apply_archive_bytes(data: bytes, cfg: Dict[str, Any]) -> List[str]:
    root_prefix = (cfg.get("repo_root_prefix") or "").strip()
    changed: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if root_prefix and name.startswith(root_prefix):
                rel = name[len(root_prefix):]
            else:
                rel = name
            if not _should_include(rel, cfg):
                continue
            # write file
            target = Path(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            changed.append(rel)
    return changed

async def _pull_archive_and_apply(cfg: Dict[str, Any]) -> List[str]:
    url = cfg.get("archive")
    if not url:
        return []
    timeout = int(cfg.get("timeout_s", 20))
    async with aiohttp.ClientSession() as s:
        data = await _fetch_bytes(s, url, timeout)
        return _apply_archive_bytes(data, cfg)

def _load_cfg() -> Dict[str, Any]:
    # Pure file config; NO ENV required
    p = Path("config") / "remote_sync.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {
            "base": "",
            "archive": "",
            "repo_root_prefix": "",
            "pull_sets": [
                {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
                {"include": ["satpambot/"], "allow_exts": ["py"]},
            ],
            "files": [],
            "timeout_s": 20,
        }

# ---------- Restart helpers (NO-ENV) ----------

ACK_DELAY = 2.0  # seconds, fixed (no env)
GUARD_FILE = "/tmp/satpambot_restart.lock"
GUARD_WINDOW = 240  # seconds

def _reexec_inplace():
    py = sys.executable
    os.execv(py, [py, *sys.argv])

def _guard_status():
    p = Path(GUARD_FILE)
    if p.exists():
        try:
            age = (asyncio.get_event_loop().time() - p.stat().st_mtime)
        except Exception:
            # fallback to wall clock seconds; precision not critical
            import time
            age = time.time() - p.stat().st_mtime
        return True, age
    return False, None

def _guard_should_restart():
    exists, age = _guard_status()
    return not (exists and age is not None and age < GUARD_WINDOW), age

def _guard_mark(reason="unknown"):
    try:
        Path(GUARD_FILE).write_text(json.dumps({"t": os.times(), "reason": reason}))
        return True
    except Exception:
        return False

# ---------- Cog: /repo & /runtime (archive-based) ----------

class RemoteSyncRestart(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="repo", description="Remote pull & restart (ZIP-friendly)")
    group_rt = app_commands.Group(name="runtime", description="Runtime ops")

    @group.command(name="pull", description="Tarik update dari GitHub archive (tanpa deploy)")
    async def pull(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.defer(ephemeral=True, thinking=True)
        cfg = _load_cfg()
        try:
            changed = await _pull_archive_and_apply(cfg)
        except Exception as e:
            return await itx.followup.send(f"❌ Gagal pull: `{e}`", ephemeral=True)
        await itx.followup.send(f"✅ Selesai. File yang berubah: {changed or '-'}", ephemeral=True)

    @group.command(name="pull_and_restart", description="Tarik update & restart (ACK dulu, lalu re-exec)")
    async def pull_and_restart(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.defer(ephemeral=True, thinking=True)
        ok, age = _guard_should_restart()
        if not ok:
            return await itx.followup.send(f"⏱️ Restart sudah dipicu {int(age or 0)}s lalu — di-skip.", ephemeral=True)
        cfg = _load_cfg()
        try:
            changed = await _pull_archive_and_apply(cfg)
        except Exception as e:
            return await itx.followup.send(f"❌ Gagal pull: `{e}`", ephemeral=True)
        _guard_mark("pull_and_restart")
        await itx.followup.send(f"✅ Berubah: {len(changed)} file. Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _delay():
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_delay())

    @group_rt.command(name="restart", description="Restart cepat (ACK lalu re-exec)")
    async def rt_restart(self, itx: discord.Interaction):
        if not itx.user.guild_permissions.manage_guild:
            return await itx.response.send_message("Butuh izin Manage Server.", ephemeral=True)
        await itx.response.send_message(f"🔁 Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _delay():
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_delay())

# Auto-register & auto-sync to all guilds WITHOUT ENV
async def _sync_all_guilds_once(bot: commands.Bot):
    await bot.wait_until_ready()
    try:
        ids = [g.id for g in bot.guilds]
        for gid in ids:
            try:
                await bot.tree.sync(guild=discord.Object(id=gid))
            except Exception:
                pass
        log.info("[remote_sync_restart] auto-synced to guilds: %s", ", ".join(map(str, ids)) or "-")
    except Exception as e:
        log.warning("[remote_sync_restart] sync warn: %r", e)

async def setup(bot: commands.Bot):
    cog = RemoteSyncRestart(bot)
    await bot.add_cog(cog)
    # register groups globally (tree handles per-guild overrides after sync)
    bot.tree.add_command(cog.group, override=True)
    bot.tree.add_command(cog.group_rt, override=True)
    # schedule per-guild sync once without any ENV
    asyncio.create_task(_sync_all_guilds_once(bot))
