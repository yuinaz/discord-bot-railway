"""
Auto delete messages in focus log channel (v8)
- Deletes NON-pinned messages older than TTL seconds.
- Never touches messages that contain keeper markers like "SATPAMBOT_PHASH_DB_V1"
  or "presence=online" or have attachments we use as DB blobs.
- Runs quietly every ~45s.
Env:
    LOG_CHANNEL_ID  (required)
    LOG_AUTODELETE_TTL  default: 180
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Iterable

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

KEEPER_HINTS = (
    "SATPAMBOT_PHASH_DB_V1",
    "presence=online",
    "SATPAMBOT_STATUS_V1",
    "keeper",
    "[auto_prune_state]",
)

def _int_env(name: str, default: int | None = None):
    v = os.getenv(name, "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default

class AutoCleanLogChannel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.focus_id = _int_env("LOG_CHANNEL_ID")
        self.ttl = _int_env("LOG_AUTODELETE_TTL", 180) or 180
        self.loop.start()

    def cog_unload(self):
        self.loop.cancel()

    def _is_keeper(self, m: discord.Message) -> bool:
        if m.pinned:
            return True
        content = (m.content or "").lower()
        for hint in KEEPER_HINTS:
            if hint.lower() in content:
                return True
        return False

    @tasks.loop(seconds=45.0)
    async def loop(self):
        if not self.focus_id:
            return
        try:
            # Focus channel only
            ch = None
            for g in self.bot.guilds:
                tmp = g.get_channel(self.focus_id) or await self.bot.fetch_channel(self.focus_id)
                if tmp:
                    ch = tmp
                    break
            if ch is None or not isinstance(ch, discord.TextChannel):
                return
            cutoff = discord.utils.utcnow().timestamp() - self.ttl
            async def _check(m: discord.Message) -> bool:
                if self._is_keeper(m):
                    return False
                # keep pinned, system, and thread starter
                if m.flags and getattr(m.flags, "is_crossposted", False):
                    return False
                ts = m.created_at.timestamp() if m.created_at else time.time()
                return ts < cutoff

            await ch.purge(limit=200, check=_check, bulk=True, oldest_first=True, reason="auto-clean focus log")
        except Exception as e:
            log.debug("[log_autodelete_focus] purge skipped: %r", e)

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoCleanLogChannel(bot))
    log.debug("[log_autodelete_focus] ready (ttl=%ss)", _int_env("LOG_AUTODELETE_TTL", 180) or 180)
