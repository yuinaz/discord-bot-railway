
import asyncio, json, os, io, zipfile, logging, pathlib, shutil
from typing import List, Dict, Any, Optional
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
        for k, v in (data.items() if isinstance(data, dict) else []):
            if v is not None:
                out[k] = v
        return out
    except Exception as e:
        log.warning("[repo_slash_simple] cannot read %s: %s; using defaults", CONFIG_SYNC, e)
        return DEFAULT_REMOTE.copy()

def _norm_slash(s: str) -> str:
    # Windows-safe normalization
    return s.replace("\\\\", "/").replace("\\", "/")

def _allowed(rel: str, pull_sets: List[Dict[str, Any]]) -> bool:
    rel_slash = _norm_slash(rel)
    if rel_slash.endswith("/"):
        return False
    ext = rel_slash.rsplit(".", 1)[-1].lower() if "." in rel_slash else ""
    for spec in pull_sets or []:
        includes = [_norm_slash(p) for p in spec.get("include", [])]
        allow_exts = [e.lower() for e in spec.get("allow_exts", [])]
        for inc in includes:
            if rel_slash.startswith(inc):
                if (not allow_exts) or (ext in allow_exts):
                    return True
    return False

async def _download(url: str, timeout_s: int) -> bytes:
    # Prefer aiohttp; fallback to urllib if not available
    try:
        import aiohttp  # type: ignore
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                resp.raise_for_status()
                return await resp.read()
    except Exception as e:
        log.warning("[repo_slash_simple] aiohttp failed (%s); fallback to urllib", e)
        import urllib.request
        with urllib.request.urlopen(url, timeout=timeout_s) as r:
            return r.read()

def _apply_zip_filtered(data: bytes, repo_root_prefix: str, pull_sets: List[Dict[str, Any]]) -> Dict[str, Any]:
    zf = zipfile.ZipFile(io.BytesIO(data))
    total = 0
    written = 0
    skipped = 0
    base = repo_root_prefix or ""
    for zi in zf.infolist():
        name = zi.filename
        if base and (not name.startswith(base)):
            continue
        rel = name[len(base):] if base else name
        if (not rel) or rel.endswith("/"):
            continue
        total += 1
        if not _allowed(rel, pull_sets):
            skipped += 1
            continue
        target = pathlib.Path(_norm_slash(rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(zi) as src, open(target, "wb") as dst:
            dst.write(src.read())
        written += 1
    return {"total": total, "written": written, "skipped": skipped}

def _safe_target_dir(s: Optional[str]) -> pathlib.Path:
    base = pathlib.Path.cwd().resolve()
    name = (s or "_upstream_full").strip() or "_upstream_full"
    name = _norm_slash(name).lstrip("/")
    parts = [p for p in name.split("/") if p and p != ".."]
    name = "/".join(parts) or "_upstream_full"
    target = (base / name).resolve()
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise RuntimeError("target path escapes workspace")
    return target

def _apply_zip_full_to_dir(data: bytes, repo_root_prefix: str, target_dir: pathlib.Path) -> Dict[str, Any]:
    zf = zipfile.ZipFile(io.BytesIO(data))
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    base = repo_root_prefix or ""
    for zi in zf.infolist():
        name = zi.filename
        if base and (not name.startswith(base)):
            continue
        rel = _norm_slash(name[len(base):] if base else name)
        if not rel:
            continue
        dest = (target_dir / rel)
        if rel.endswith("/"):
            dest.mkdir(parents=True, exist_ok=True)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(zi) as src, open(dest, "wb") as dst:
            dst.write(src.read())
        total += 1
    return {"total": total, "written": total, "target": str(target_dir)}

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[repo_slash_simple] init")

    # --- alias commands (top-level; optional) ---
    @app_commands.command(name="pull_and_restart", description="Pull latest (filtered) & restart (alias)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alias_pull_and_restart(self, itx: discord.Interaction):
        await self._pull_and_restart(itx)

    @app_commands.command(name="repo_pull", description="Pull latest (filtered) & apply (alias)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alias_repo_pull(self, itx: discord.Interaction):
        await self._pull_only(itx)

    # --- group callbacks (bound in cog_load) ---
    @app_commands.checks.has_permissions(manage_guild=True)
    async def grp_pull(self, itx: discord.Interaction):
        await self._pull_only(itx)

    @app_commands.checks.has_permissions(manage_guild=True)
    async def grp_pull_and_restart(self, itx: discord.Interaction):
        await self._pull_and_restart(itx)

    @app_commands.checks.has_permissions(manage_guild=True)
    async def grp_restart(self, itx: discord.Interaction):
        await itx.response.send_message("Restarting process…", ephemeral=True)
        await itx.followup.send("💤 Exiting now, Render will restart the service.", ephemeral=True)
        await asyncio.sleep(0.8)
        os._exit(0)

    @app_commands.describe(target="Folder tujuan relatif di server (default: _upstream_full)")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def grp_pull_full(self, itx: discord.Interaction, target: Optional[str] = None):
        r = _load_remote()
        await itx.response.send_message("⬇️ Mengunduh FULL archive ke folder target…", ephemeral=True)
        data = await _download(r.get("archive", DEFAULT_REMOTE["archive"]), int(r.get("timeout_s", 25)))
        tgt = _safe_target_dir(target)
        stats = _apply_zip_full_to_dir(data, r.get("repo_root_prefix", DEFAULT_REMOTE["repo_root_prefix"]), tgt)
        await itx.followup.send(f"✅ Full mirror siap di `{stats['target']}` (files={stats['written']}).", ephemeral=True)

    async def cog_load(self):
        # Register aliases idempotently
        alias_map = {
            "pull_and_restart": self.alias_pull_and_restart,
            "repo_pull": self.alias_repo_pull,
        }
        for name, fn in alias_map.items():
            if self.bot.tree.get_command(name) is None:
                try:
                    self.bot.tree.add_command(fn)
                    log.info("[repo_slash_simple] alias /%s added", name)
                except Exception as e:
                    log.warning("[repo_slash_simple] alias /%s add failed: %s", name, e)

        # Ensure /repo group exists, else create
        existing = self.bot.tree.get_command("repo")
        if isinstance(existing, app_commands.Group):
            grp = existing
            log.info("[repo_slash_simple] attach to existing /repo")
        else:
            grp = app_commands.Group(name="repo", description="Repo maintenance (pull & restart)")
            try:
                self.bot.tree.add_command(grp)
                log.info("[repo_slash_simple] created /repo group")
            except Exception as e:
                log.warning("[repo_slash_simple] add /repo failed: %s", e)
                return

        # Add/replace specific subcommands to /repo
        def _add_or_replace(group: app_commands.Group, name: str, callback, desc: str):
            existing_cmd = None
            for c in list(group.commands):
                if c.name == name:
                    existing_cmd = c
                    break
            if existing_cmd is not None:
                try:
                    group.remove_command(existing_cmd.name)
                except Exception:
                    pass
            try:
                group.add_command(app_commands.Command(name=name, description=desc, callback=callback))
                log.info("[repo_slash_simple] /repo %s registered", name)
            except Exception as e:
                log.warning("[repo_slash_simple] /repo %s register failed: %s", name, e)

        _add_or_replace(grp, "pull", self.grp_pull, "Pull latest (filtered) and apply safe files")
        _add_or_replace(grp, "pull_and_restart", self.grp_pull_and_restart, "Pull then restart process (filtered)")
        _add_or_replace(grp, "restart", self.grp_restart, "Restart process only")
        _add_or_replace(grp, "pull_full", self.grp_pull_full, "Pull FULL archive into a local folder (mirror)")

    # --- helpers ---
    async def _pull_only(self, itx: discord.Interaction):
        await itx.response.send_message("⬇️ Downloading & applying latest archive…", ephemeral=True)
        r = _load_remote()
        data = await _download(r.get("archive", DEFAULT_REMOTE["archive"]), int(r.get("timeout_s", 20)))
        stats = _apply_zip_filtered(data, r.get("repo_root_prefix", DEFAULT_REMOTE["repo_root_prefix"]), r.get("pull_sets", DEFAULT_REMOTE["pull_sets"]))
        await itx.followup.send(f"✅ Pulled. Files total={stats['total']}, applied={stats['written']}, skipped={stats['skipped']}.", ephemeral=True)

    async def _pull_and_restart(self, itx: discord.Interaction):
        await itx.response.send_message("⬇️ Pulling latest (filtered), then restarting…", ephemeral=True)
        r = _load_remote()
        data = await _download(r.get("archive", DEFAULT_REMOTE["archive"]), int(r.get("timeout_s", 20)))
        stats = _apply_zip_filtered(data, r.get("repo_root_prefix", DEFAULT_REMOTE["repo_root_prefix"]), r.get("pull_sets", DEFAULT_REMOTE["pull_sets"]))
        await itx.followup.send(f"✅ Pulled (applied={stats['written']}, skipped={stats['skipped']}). Restarting…", ephemeral=True)
        await asyncio.sleep(0.8)
        os._exit(0)

async def setup(bot: commands.Bot):
    await bot.add_cog(RepoSlashSimple(bot))
