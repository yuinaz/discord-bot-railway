# -*- coding: utf-8 -*-
"""
LogAutoDeleteFocus — v4 (strict)
HANYA menghapus embed dengan judul persis:
  - "Maintenance"
  - "Heartbeat"
TIDAK akan menghapus "Periodic Status".

Fokus area:
- channel log-botphising: 1400375184048787566
- thread neuro-lite progress: 1425400701982478408

Konfigurasi TTL (detik):
- STICKY_DELETE_TTL (prioritas 1) atau
- LOG_AUTODELETE_TTL (prioritas 2) atau
- default 300

Catatan:
- Menghapus pesan BOT sendiri saja (lebih aman).
- Pesan pinned tetap akan dicoba dihapus bila cocok judulnya.
- Kesalahan permission akan ditangani diam-diam (log.warn).
"""
from __future__ import annotations
import os
import asyncio
import logging
from typing import Iterable, Set

try:
    import discord
    from discord.ext import commands  # type: ignore
except Exception:  # pragma: no cover - during smoke
    discord = None  # type: ignore
    commands = object  # type: ignore

log = logging.getLogger(__name__)

TARGET_CHANNEL_IDS: Set[int] = {1400375184048787566}
TARGET_THREAD_IDS: Set[int]  = {1425400701982478408}

DELETE_TITLES = {"Maintenance", "Heartbeat"}
PROTECT_TITLES = {"Periodic Status"}

def _ttl_seconds() -> int:
    for key in ("STICKY_DELETE_TTL", "LOG_AUTODELETE_TTL"):
        val = os.getenv(key)
        if val and val.isdigit():
            return int(val)
    return 300

def _in_scope(ch) -> bool:
    try:
        cid = getattr(ch, "id", None)
        parent_id = getattr(ch, "parent_id", None)
        if cid in TARGET_CHANNEL_IDS or cid in TARGET_THREAD_IDS:
            return True
        if parent_id in TARGET_CHANNEL_IDS or parent_id in TARGET_THREAD_IDS:
            return True
    except Exception:
        pass
    return False

def _title_matches(embeds: Iterable) -> bool:
    """Return True bila SALAH SATU embed.title ∈ DELETE_TITLES dan
    tidak ada yang ∈ PROTECT_TITLES (proteksi eksplisit)."""
    has_delete = False
    for e in embeds or []:
        title = getattr(e, "title", None) or ""
        if title in PROTECT_TITLES:
            return False  # proteksi keras
        if title in DELETE_TITLES:
            has_delete = True
    return has_delete

class LogAutoDeleteFocus(commands.Cog if hasattr(commands, "Cog") else object):
    def __init__(self, bot):
        self.bot = bot
        self.ttl = max(0, _ttl_seconds())
        log.info("[log_autodelete.focus:v4] aktif — TTL=%ss; titles del=%s; protect=%s; scope: ch=%s threads=%s",
                 self.ttl, sorted(DELETE_TITLES), sorted(PROTECT_TITLES),
                 sorted(TARGET_CHANNEL_IDS), sorted(TARGET_THREAD_IDS))

    async def _maybe_delete(self, message):
        try:
            if not message or not message.channel:
                return
            if message.author is None or self.bot is None:
                return
            # Hanya hapus pesan dari BOT sendiri agar aman
            if getattr(message.author, "id", None) != getattr(self.bot.user, "id", None):
                return
            ch = message.channel
            if not _in_scope(ch):
                return
            embeds = getattr(message, "embeds", None) or []
            if not embeds:
                return
            if not _title_matches(embeds):
                return

            async def do_delete():
                try:
                    await message.delete()
                except Exception as e:
                    log.warning("[log_autodelete.focus] gagal delete msg %s di ch %s: %r",
                                getattr(message, "id", "?"), getattr(ch, "id", "?"), e)

            if self.ttl <= 0:
                await do_delete()
            else:
                await asyncio.sleep(self.ttl)
                await do_delete()
        except Exception as e:
            log.exception("[log_autodelete.focus] _maybe_delete error: %r", e)

    # Listener: pesan baru
    if hasattr(commands, "Cog"):
        @commands.Cog.listener()
        async def on_message(self, message):
            await self._maybe_delete(message)

        # Listener: pesan diedit (sticky biasanya pakai edit)
        @commands.Cog.listener()
        async def on_message_edit(self, before, after):
            await self._maybe_delete(after)

def setup(bot):
    if discord is None or not hasattr(commands, "Cog"):
        log.warning("[log_autodelete.focus] discord/commands unavailable (smoke mode).")
        return
    try:
        bot.add_cog(LogAutoDeleteFocus(bot))
    except Exception:
        log.exception("[log_autodelete.focus] gagal add_cog")
