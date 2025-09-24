
from __future__ import annotations
import asyncio, json, os, time
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import discord
from discord.ext import commands
from discord import ChannelType

# reuse helpers from remote_sync_restart
from .remote_sync_restart import _load_cfg as _rs_load_cfg, _pull_archive_and_apply as _rs_pull_archive_and_apply

STATE = Path("data") / "remote_watch_state.json"
DEFAULT = {
    "enabled": True,
    "interval_days": 2,            # hemat kuota: default cek tiap 2 hari
    "interval_minutes": None,      # kalau diisi, override days
    "check_url": "",               # fallback ke remote_sync.json["archive"]
    "notify_channel_id": 0,        # ID channel #log-botphising
    "notify_thread_name": "log restart github",  # NAMA thread yang akan dipakai/dibuat otomatis
    "request_timeout_s": 15,
}

def _load_watch_cfg() -> Dict[str, Any]:
    base_cfg = _rs_load_cfg()
    watch_cfg = dict(DEFAULT)
    cfg_path = Path("config") / "remote_watch.json"
    try:
        if cfg_path.exists():
            watch_cfg.update(json.loads(cfg_path.read_text("utf-8")) or {})
    except Exception:
        pass
    if not (watch_cfg.get("check_url") or "").strip():
        watch_cfg["check_url"] = base_cfg.get("archive") or ""
    return watch_cfg

def _load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE.read_text("utf-8"))
    except Exception:
        return {"etag": "", "last_modified": "", "last_checked": 0, "last_updated": 0}

def _save_state(s: Dict[str, Any]):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(s), encoding="utf-8")
    except Exception:
        pass

async def _get_or_create_log_thread(guild: Optional[discord.Guild], channel_id: int, name: str):
    """Ambil thread bernama 'name' di dalam channel_id; kalau tidak ada → buat.
       - Cari di active threads
       - Coba cari di archived (public) lalu unarchive
       - Jika tetap tidak ada → create public thread
    """
    if not guild or not channel_id:
        return None
    ch = guild.get_channel(channel_id)
    if isinstance(ch, discord.Thread):
        return ch
    if not isinstance(ch, discord.TextChannel):
        return None

    target_name = (name or "").strip().lower()
    if not target_name:
        return ch  # fallback: kirim ke channel

    # 1) Cari di active threads
    try:
        for t in ch.threads:
            try:
                if (t.name or "").strip().lower() == target_name and not t.archived:
                    return t
            except Exception:
                continue
    except Exception:
        pass

    # 2) Cari di archived public threads (limit kecil untuk hemat)
    try:
        async for t in ch.archived_threads(limit=50, private=False):
            try:
                if (t.name or "").strip().lower() == target_name:
                    # unarchive supaya aktif lagi
                    try:
                        await t.edit(archived=False)
                    except Exception:
                        pass
                    return t
            except Exception:
                continue
    except Exception:
        pass

    # 3) Tidak ada → buat baru (public thread, auto-archive 7 hari)
    try:
        th = await ch.create_thread(
            name=name,
            type=ChannelType.public_thread,
            auto_archive_duration=10080  # 7 hari
        )
        return th
    except Exception:
        # fallback ke channel jika gagal buat thread
        return ch

class AutoRepoWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None
        self._started = False

    async def _check_once(self):
        watch = _load_watch_cfg()
        if not bool(watch.get("enabled", True)): 
            return False, "disabled"
        url = (watch.get("check_url") or "").strip()
        if not url:
            return False, "no check url"

        timeout_s = int(watch.get("request_timeout_s", 15))
        state = _load_state()
        headers = {}
        if state.get("etag"): headers["If-None-Match"] = state["etag"]
        if state.get("last_modified"): headers["If-Modified-Since"] = state["last_modified"]

        status = None
        etag = None
        last_mod = None
        # HEAD untuk hemat bandwidth
        try:
            async with aiohttp.ClientSession() as s:
                async with s.head(url, timeout=timeout_s, headers=headers) as r:
                    status = r.status
                    etag = r.headers.get("ETag") or r.headers.get("Etag")
                    last_mod = r.headers.get("Last-Modified")
        except Exception:
            # fallback GET (jarang)
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(url, timeout=timeout_s, headers=headers) as r:
                        status = r.status
                        etag = r.headers.get("ETag") or r.headers.get("Etag")
                        last_mod = r.headers.get("Last-Modified")
            except Exception:
                status = None

        state["last_checked"] = int(time.time())

        if status == 304:
            _save_state(state)
            return False, "not-modified"

        if status and 200 <= status < 300:
            changed = False
            if etag and etag != state.get("etag"):
                changed = True
            elif (not etag) and last_mod and last_mod != state.get("last_modified"):
                changed = True
            elif not state.get("etag") and not state.get("last_modified"):
                # run pertama → simpan state saja, tanpa restart/log (hindari loop)
                state["etag"] = etag or ""
                state["last_modified"] = last_mod or ""
                _save_state(state)
                return False, "primed"
            if changed:
                state["etag"] = etag or state.get("etag","")
                state["last_modified"] = last_mod or state.get("last_modified","")
                state["last_updated"] = int(time.time())
                _save_state(state)

                # Pull & restart bila ada perubahan file nyata
                base_cfg = _rs_load_cfg()
                changed_files = await _rs_pull_archive_and_apply(base_cfg)
                if changed_files:
                    try:
                        guild = self.bot.guilds[0] if self.bot.guilds else None
                        target = await _get_or_create_log_thread(
                            guild,
                            int(watch.get("notify_channel_id") or 0),
                            str(watch.get("notify_thread_name") or "log restart github")
                        )
                        if target and isinstance(target, (discord.TextChannel, discord.Thread)):
                            txt = f"[repo-watch] {len(changed_files)} file berubah → restarting…"
                            await target.send(txt)
                    except Exception:
                        pass
                    await asyncio.sleep(1.5)
                    os._exit(0)
                else:
                    return False, "no-file-changes"
            return False, "no-change"
        _save_state(state)
        return False, f"status={status}"

    def _sleep_seconds(self) -> int:
        watch = _load_watch_cfg()
        days = watch.get("interval_days", None)
        if days is not None:
            try: d = int(days)
            except Exception: d = 2
            d = max(1, min(30, d))  # clamp
            return d * 86400
        try: mins = int(watch.get("interval_minutes") or 15)
        except Exception: mins = 15
        mins = max(5, min(30*24*60, mins))
        return mins * 60

    async def _runner(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await self._check_once()
            except Exception:
                pass
            await asyncio.sleep(self._sleep_seconds())

    @commands.Cog.listener()
    async def on_ready(self):
        if self._started: return
        self._started = True
        self._task = asyncio.create_task(self._runner())

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRepoWatcher(bot))
