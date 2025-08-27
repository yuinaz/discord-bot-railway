# satpambot/bot/modules/discord_bot/cogs/anti_image_phish_guard.py
from __future__ import annotations

import asyncio
import json
import os
from satpambot.bot.modules.discord_bot.helpers import modlog
from ..helpers import guard_state  # dedupe shared
from pathlib import Path
from typing import List, Dict, Any, Optional

import discord
from discord.ext import commands, tasks

try:
    import aiohttp  # discord.py uses aiohttp, should be available
except Exception:  # pragma: no cover
    aiohttp = None

# --- Tuning ---
PHASH_THRESHOLD = 8
AUTOBAN = False

# Candidate files where dashboard writes pHash entries (first that exists will be used)
PHASH_DB_CANDIDATES = [
    Path("satpambot/dashboard/data/phash_index.json"),
    Path("satpambot/dashboard/phash_index.json"),
    Path("satpambot/dashboard/.data/phash_index.json"),
    Path("data/phash_index.json"),
    Path("/data/phash_index.json"),
    Path("/tmp/phash_index.json"),
]

# Optionally allow override by env without requiring it
ENV_PATH = os.getenv("SATPAMBOT_PHASH_DB")
if ENV_PATH:
    PHASH_DB_CANDIDATES.insert(0, Path(ENV_PATH))

def _load_from_file() -> List[Dict[str, Any]]:
    for p in PHASH_DB_CANDIDATES:
        try:
            if p.exists():
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            continue
    return []

async def _load_from_http() -> List[Dict[str, Any]]:
    if aiohttp is None:
        return []
    # Try local Flask origin
    port = os.getenv("PORT", "5000")
    candidates = [
        f"http://127.0.0.1:{port}/api/phish/phash",
        f"http://localhost:{port}/api/phish/phash",
        "http://127.0.0.1:3115/api/phish/phash",
    ]
    async with aiohttp.ClientSession() as s:
        for url in candidates:
            try:
                async with s.get(url, timeout=3) as r:
                    if r.status == 200:
                        j = await r.json()
                        if isinstance(j, list):
                            return j
            except Exception:
                continue
    return []

class AntiImagePhishGuard(commands.Cog):


    def _apply_lists(self, lists_dict):
        try:
            self._wl_domains = set(lists_dict.get("wl_domains") or [])
            self._wl_patterns = lists_dict.get("wl_patterns") or []
            self._bl_domains = set(lists_dict.get("bl_domains") or [])
            self._bl_patterns = lists_dict.get("bl_patterns") or []
        except Exception:
            pass

    def _nsfw_soft_exempt_thread(self, message: discord.Message) -> bool:
        ch = message.channel
        if isinstance(ch, discord.Thread):
            tname = (getattr(ch, "name", "") or "").lower()
            if tname and any(tname == n for n in NSFW_SOFT_THREAD_NAMES):
                return True
        return False

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._phash_entries: List[Dict[str, Any]] = []
        self.threshold = PHASH_THRESHOLD
        self.autoban = AUTOBAN
        self._reload_task.start()

    # Public accessor if other cogs need it
    def phash_count(self) -> int:
        return len(self._phash_entries)

    # -------------- loading logic --------------
    async def _reload_once(self) -> None:
        new = _load_from_file()
        if not new:
            try:
                new = await _load_from_http()
            except Exception:
                new = []
        self._phash_entries = new or []
        print(f"[phish] load phash={len(self._phash_entries)} threshold={self.threshold} autoban={self.autoban}")

    @tasks.loop(seconds=60)
    async def _reload_task(self):
        await self._reload_once()

    @_reload_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        # initial load
        await self._reload_once()

    # -------------- (placeholder) detection hooks --------------
    # Implement your image message handlers here using self._phash_entries,
    # threshold (self.threshold) and autoban flag (self.autoban).
    # The structure of each entry in _phash_entries should match what your
    # dashboard uploader produces (e.g., {"hash": ..., "reason": ..., "by": ..., "at": ...}).

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishGuard(bot))
