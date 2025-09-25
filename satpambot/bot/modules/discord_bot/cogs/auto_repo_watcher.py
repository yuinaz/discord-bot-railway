# auto_repo_watcher.py — STABILIZE PATCH (no-env)
# - Boot cooldown: jangan restart dalam 180s pertama setelah start
# - Restart guard: cegah restart beruntun
# - Archive SHA cache: skip kalau ZIP sama
# - Diff-aware apply: tulis file hanya jika konten berubah
# - Restart via os.execv (bukan os._exit) agar Render tidak menandai "Instance failed"
from __future__ import annotations
import asyncio, aiohttp, hashlib, io, json, os, sys, zipfile, time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers import restart_guard as rg

BOOT_T0 = time.monotonic()
BOOT_COOLDOWN_S = 180.0  # no restart in first 3 minutes
SHA_CACHE_FILE = Path("/tmp/satpambot_last_archive.sha256")

def _load_watch_cfg() -> Dict[str, Any]:
    p = Path("config") / "remote_watch.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"enabled": False, "interval_days": 4, "notify_thread_name": "log restart github"}

def _load_sync_cfg() -> Dict[str, Any]:
    p = Path("config") / "remote_sync.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {
            "archive": "",
            "repo_root_prefix": "",
            "pull_sets": [
                {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
                {"include": ["satpambot/"], "allow_exts": ["py"]},
            ],
            "files": [],
            "timeout_s": 20,
        }

async def _fetch_bytes(url: str, timeout: int) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            r.raise_for_status()
            return await r.read()

def _should_include(name: str, cfg: Dict[str, Any]) -> bool:
    pulls = cfg.get("pull_sets") or []
    name_l = name.lower()
    for rule in pulls:
        inc = rule.get("include") or []
        exts = [e.lower() for e in (rule.get("allow_exts") or [])]
        if inc and not any(name.startswith(i) for i in inc):
            continue
        if exts and not any(name_l.endswith("." + e) for e in exts):
            continue
        return True
    return False

def _apply_archive_bytes_if_changed(data: bytes, cfg: Dict[str, Any]) -> Tuple[List[str], int]:
    """Extract only changed files. Returns (changed_paths, total_considered)."""
    root_prefix = (cfg.get("repo_root_prefix") or "").strip()
    changed: List[str] = []
    considered = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            rel = name[len(root_prefix):] if root_prefix and name.startswith(root_prefix) else name
            if not _should_include(rel, cfg):
                continue
            considered += 1
            target = Path(rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            new_bytes = z.read(info)
            if target.exists():
                try:
                    with open(target, "rb") as f:
                        old_bytes = f.read()
                    if old_bytes == new_bytes:
                        continue  # skip identical
                except Exception:
                    pass
            with open(target, "wb") as f:
                f.write(new_bytes)
            changed.append(rel)
    return changed, considered

async def _pull_archive_and_apply_if_changed() -> Tuple[List[str], str]:
    """Download archive; skip if same SHA as last time; apply only changed files."""
    cfg = _load_sync_cfg()
    url = cfg.get("archive")
    if not url:
        return [], "no-archive-url"
    timeout = int(cfg.get("timeout_s", 20))
    data = await _fetch_bytes(url, timeout)
    sha = hashlib.sha256(data).hexdigest()
    if SHA_CACHE_FILE.exists():
        try:
            last = SHA_CACHE_FILE.read_text("utf-8").strip()
            if last == sha:
                return [], "same-zip"  # skip
        except Exception:
            pass
    changed, considered = _apply_archive_bytes_if_changed(data, cfg)
    try:
        SHA_CACHE_FILE.write_text(sha)
    except Exception:
        pass
    return changed, "applied" if changed else "no-diff"

class AutoRepoWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = asyncio.create_task(self._runner())

    async def _runner(self):
        cfg = _load_watch_cfg()
        if not cfg.get("enabled", False):
            return
        # Initial delay kecil supaya tidak langsung restart setelah deploy
        await asyncio.sleep(60.0)
        interval_days = float(cfg.get("interval_days", 4))
        interval_s = max(1800.0, interval_days * 86400.0)  # min 30m
        thread_name = cfg.get("notify_thread_name") or "log restart github"

        while True:
            try:
                changed, mode = await _pull_archive_and_apply_if_changed()
                if changed:
                    ok, age = rg.should_restart()
                    uptime = time.monotonic() - BOOT_T0
                    if ok and uptime >= BOOT_COOLDOWN_S:
                        # Announce before restart
                        try:
                            # Try to post to a thread named 'thread_name' if you have a helper elsewhere
                            ch = None
                            # (Optional) integrate with your logging cog; left as no-op to avoid coupling
                        except Exception:
                            pass
                        rg.mark("watcher")
                        await asyncio.sleep(1.5)
                        os.execv(sys.executable, [sys.executable, *sys.argv])
                    else:
                        # Debounced; skip restart this cycle
                        pass
                else:
                    # mode can be 'same-zip' or 'no-diff' — do nothing
                    pass
            except Exception:
                # swallow and keep looping
                pass
            await asyncio.sleep(interval_s)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRepoWatcher(bot))
