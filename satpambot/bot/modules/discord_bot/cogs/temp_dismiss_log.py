# -*- coding: utf-8 -*-
"""
temp_dismiss_log.py (v2, no-ENV)
---------------------------------
Auto-hapus (dismiss) pesan log tertentu setelah 60 detik TANPA butuh ENV.
Target:
- Pesan dari bot di channel #log-botphising (atau thread di bawahnya)
- Embed judul: "Lists updated" atau "Phish image registered" (case-insensitive)
Tujuan: log whitelist/blacklist & image-hash tidak menimbun chat lain.

Catatan izin:
- Bot cukup bisa menghapus pesannya sendiri. Untuk jaga-jaga, beri "Manage Messages" di channel log.
"""
from __future__ import annotations
import asyncio
from typing import List

import discord
from discord.ext import commands

CHANNEL_NAME = "log-botphising"
DISMISS_AFTER_SEC = 60
TARGET_TITLES = {"lists updated", "phish image registered", "phish hash registered", "image hash registered"}

class TempDismissLog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _in_log_area(self, ch: discord.abc.MessageableChannel) -> bool:
        # true jika channel adalah #log-botphising atau thread di bawahnya
        try:
            if isinstance(ch, discord.TextChannel):
                return (ch.name or "").lower() == CHANNEL_NAME
            if isinstance(ch, discord.Thread):
                parent = ch.parent
                return bool(parent and (parent.name or "").lower() == CHANNEL_NAME)
        except Exception:
            return False
        return False

    def _is_target_embed(self, embeds: List[discord.Embed]) -> bool:
        for e in embeds or []:
            title = (e.title or "").strip().lower()
            if title in TARGET_TITLES:
                return True
        return False

    async def _delete_later(self, msg: discord.Message):
        await asyncio.sleep(DISMISS_AFTER_SEC)
        try:
            await msg.delete()
        except Exception:
            pass  # no perms / already deleted

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # hanya proses pesan bot sendiri agar aman
        if message.author != self.bot.user:
            return
        if not self._in_log_area(message.channel):
            return
        if not message.embeds or not self._is_target_embed(message.embeds):
            return
        # jadwalkan penghapusan
        self.bot.loop.create_task(self._delete_later(message))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # jaga-jaga kalau embed baru ditambahkan via edit
        if after.author != self.bot.user:
            return
        if not self._in_log_area(after.channel):
            return
        if not after.embeds or not self._is_target_embed(after.embeds):
            return
        self.bot.loop.create_task(self._delete_later(after))

async def setup(bot: commands.Bot):
    await bot.add_cog(TempDismissLog(bot))

def setup_old(bot: commands.Bot):
    bot.add_cog(TempDismissLog(bot))
