# -*- coding: utf-8 -*-
"""
temp_dismiss_log.py (targeted v2.6b)
------------------------------------
HANYA hapus pesan bot dengan embed-title berikut (case-insensitive, exact):
  - "Lists updated"
  - "Phish image registered"

Ruang lingkup:
- Channel #log-botphising dan semua thread di bawahnya
- KECUALI thread "memory W*B" (tidak pernah dihapus)
- Pesan lama (>=60 dtk) ikut dibersihkan SEKALI saat startup (backfill)
- TANPA ENV

Catatan izin: hapus pesan bot sendiri biasanya cukup; untuk aman beri Manage Messages di channel log.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from typing import List

import discord
from discord.ext import commands

CHANNEL_NAME = "log-botphising"
EXCLUDED_THREAD_NAME = "memory W*B"
DISMISS_AFTER_SEC = 60
TARGET_TITLES = {"lists updated", "phish image registered"}  # exact, case-insensitive

class TempDismissLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._backfill_done = False

    # ---------- helpers ----------
    def _in_log_area(self, ch: discord.abc.MessageableChannel) -> bool:
        try:
            if isinstance(ch, discord.TextChannel):
                return (ch.name or "").lower() == CHANNEL_NAME
            if isinstance(ch, discord.Thread):
                parent = ch.parent
                if not parent:
                    return False
                if (ch.name or "").lower() == EXCLUDED_THREAD_NAME.lower():
                    return False
                return (parent.name or "").lower() == CHANNEL_NAME
        except Exception:
            return False
        return False

    def _matches_target(self, embeds: List[discord.Embed]) -> bool:
        for e in embeds or []:
            title = (e.title or "").strip().lower()
            if title in TARGET_TITLES:
                return True
        return False

    async def _delete_at_60s(self, msg: discord.Message):
        try:
            created = msg.created_at
            if created and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age = (now - created).total_seconds() if created else 0.0
            delay = max(0.0, DISMISS_AFTER_SEC - age)
            await asyncio.sleep(delay)
            await msg.delete()
        except Exception:
            pass  # ignore perms or already deleted

    # ---------- listeners ----------
    @commands.Cog.listener()
    async def on_ready(self):
        if not self._backfill_done:
            await self._backfill_cleanup()
            self._backfill_done = True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author != self.bot.user:
            return
        if not self._in_log_area(message.channel):
            return
        if not message.embeds or not self._matches_target(message.embeds):
            return
        # schedule deletion exactly at 60s age
        self.bot.loop.create_task(self._delete_at_60s(message))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author != self.bot.user:
            return
        if not self._in_log_area(after.channel):
            return
        if not after.embeds or not self._matches_target(after.embeds):
            return
        self.bot.loop.create_task(self._delete_at_60s(after))

    # ---------- backfill sekali saat startup ----------
    async def _backfill_cleanup(self):
        await self.bot.wait_until_ready()
        try:
            for guild in self.bot.guilds:
                # cari channel log
                ch = discord.utils.find(
                    lambda c: isinstance(c, discord.TextChannel) and (c.name or "").lower() == CHANNEL_NAME,
                    guild.text_channels
                )
                if not ch:
                    continue
                # bersihkan channel utama
                await self._clean_one(ch)
                # bersihkan thread aktif
                for th in ch.threads:
                    if (th.name or "").lower() == EXCLUDED_THREAD_NAME.lower():
                        continue
                    await self._clean_one(th)
                # bersihkan thread arsip terbaru (opsional)
                try:
                    archived = await ch.archived_threads(limit=10).flatten()
                    for th in archived:
                        if (th.name or "").lower() == EXCLUDED_THREAD_NAME.lower():
                            continue
                        await self._clean_one(th)
                except Exception:
                    pass
        except Exception:
            pass

    async def _clean_one(self, ch: discord.abc.MessageableChannel):
        try:
            async for m in ch.history(limit=150):
                if m.author != self.bot.user:
                    continue
                if not m.embeds or not self._matches_target(m.embeds):
                    continue
                # hapus yang umurnya >= 60s
                created = m.created_at
                if created and created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created:
                    age = (datetime.now(timezone.utc) - created).total_seconds()
                    if age >= DISMISS_AFTER_SEC:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(TempDismissLog(bot))

def setup_old(bot: commands.Bot):
    bot.add_cog(TempDismissLog(bot))
