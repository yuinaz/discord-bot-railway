
from __future__ import annotations
import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Iterable

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# === Hardcoded IDs (tidak pakai ENV) ===
LOG_CHANNEL_ID: int = 1400375184048787566
PROGRESS_THREAD_ID: int = 1425400701982478408
QNA_CHANNEL_IDS: tuple[int, ...] = (1426571542627614772,)

# === Konfigurasi XP (inline) ===
# TK total 2000 (L1=1000, L2=1000)
TK_L1: int = 1000
TK_L2: int = 1000
TK_TOTAL: int = TK_L1 + TK_L2

# Cooldown pemberian XP per author (agar tidak +1 terus)
PER_AUTHOR_COOLDOWN_SEC: int = 20

# Maksimal pesan yang dibaca saat catch-up
MAX_HISTORY_PER_CHANNEL: int = 300

class XpHistoryAutoCatchup(commands.Cog):
    """Autocatchup XP dari riwayat chat.
    Aman di smoke test: tidak akses bot.loop pada __init__.
    Task baru dibuat saat on_ready.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._started = False
        # memory untuk cooldown per author dan pesan yang sudah dihitung
        self._author_last_gain: dict[int, float] = {}
        self._seen_message_ids: set[int] = set()

    async def cog_unload(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await self._task

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        # Hindari dobel start
        if self._started:
            return
        self._started = True
        try:
            self._task = asyncio.create_task(self._runner(), name="xp_history_autocatchup")
        except RuntimeError:
            # Tidak ada running loop (misal smoke env) — aman: tidak ngebuat task
            log.debug("[xp_history_autocatchup] no running loop, skip runner scheduling")

    # ====== Utility XP ======
    def _xp_for_message(self, msg: discord.Message) -> int:
        # Aturan termudah: 1 XP per pesan yang bukan bot/system & ada konten
        if msg.author.bot:
            return 0
        if not (msg.content or msg.attachments):
            return 0
        # Anti spam: cooldown per author
        now = asyncio.get_event_loop().time()
        last = self._author_last_gain.get(msg.author.id, 0.0)
        if (now - last) < PER_AUTHOR_COOLDOWN_SEC:
            return 0
        self._author_last_gain[msg.author.id] = now
        return 1

    def _level_name(self, total: int) -> str:
        if total < TK_L1:
            return "TK-L1"
        if total < TK_TOTAL:
            return "TK-L2"
        # Lanjut ke SD jika melewati TK total
        over = total - TK_TOTAL
        # Mapping sederhana untuk label SD
        if over < 1000:
            return "SD-L1"
        elif over < 2000:
            return "SD-L2"
        else:
            return "SD"

    async def _award_xp(self, user_id: int, amount: int) -> None:
        # Placeholder: integrasi ke XP store internal lain dapat ditambahkan di sini.
        # Untuk visibilitas, kita log saja. Modul lain (learning_passive_observer) yang update total.
        if amount <= 0:
            return
        log.info("[xp_history_autocatchup] +%s XP to user=%s", amount, user_id)

    # ====== Runner utama ======
    async def _runner(self) -> None:
        # Tunda sedikit sampai cache/guild siap
        await asyncio.sleep(5)
        log.info("[xp_history_autocatchup] runner start")

        # Kumpulkan target channel
        targets: list[int] = [LOG_CHANNEL_ID, PROGRESS_THREAD_ID]
        targets.extend(QNA_CHANNEL_IDS)

        for channel_id in targets:
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                # Coba fetch bila tidak ada di cache
                with contextlib.suppress(Exception):
                    channel = await self.bot.fetch_channel(channel_id)  # type: ignore
            if channel is None:
                log.warning("[xp_history_autocatchup] channel %s tidak ditemukan", channel_id)
                continue

            # Ambil history — aman bila tipe channel mendukung
            try:
                async for msg in channel.history(limit=MAX_HISTORY_PER_CHANNEL, oldest_first=True):  # type: ignore
                    if msg.id in self._seen_message_ids:
                        continue
                    self._seen_message_ids.add(msg.id)
                    amount = self._xp_for_message(msg)
                    if amount > 0:
                        await self._award_xp(msg.author.id, amount)
            except Exception as e:
                log.warning("[xp_history_autocatchup] gagal baca history %s: %r", channel_id, e)

        log.info("[xp_history_autocatchup] runner finish")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(XpHistoryAutoCatchup(bot))
