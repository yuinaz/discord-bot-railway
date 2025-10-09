# -*- coding: utf-8 -*-
"""delete_safe_shim_plus.py
Proteksi kuat: pinned + keeper (presence/neuro-memory) + log session-scope.
- Mencegah penghapusan pesan DIPIN.
- Mencegah hapus pesan keeper: "presence::keeper" / "neuro-memory::keeper" di thread neuro.
- Mencegah hapus pesan di LOG_CHANNEL_ID yang dibuat SEBELUM bot online (session-only autodelete).
"""
from __future__ import annotations
import os, logging, contextlib, time
from typing import Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

STARTUP_TS = 1760009946
DEFAULT_NEURO_THREAD = os.getenv("NEURO_THREAD_NAME", "neuro-lite progress").strip().lower()

def _int_env(name: str) -> Optional[int]:
    v = (os.getenv(name) or "").strip()
    try:
        return int(v) if v else None
    except Exception:
        return None

LOG_CH_ID = _int_env("LOG_CHANNEL_ID")

def setup_delete_guard():
    orig_delete = discord.Message.delete

    async def _safe_delete(self: discord.Message, *a, **kw):
        try:
            # 0) Always protect pinned
            if getattr(self, "pinned", False):
                log.info("[delete_safe_plus] ignore delete for pinned in #%s",
                         getattr(getattr(self, "channel", None), "name", "?"))
                return

            ch = getattr(self, "channel", None)
            ch_name = (getattr(ch, "name", "") or "").strip().lower()

            # 1) Protect presence/neuro keeper in neuro thread
            if isinstance(ch, discord.Thread) and ch_name == DEFAULT_NEURO_THREAD:
                text = (getattr(self, "content", "") or "")
                if ("neuro-memory::keeper" in text) or ("presence::keeper" in text):
                    log.info("[delete_safe_plus] ignore delete for keeper in #neuro thread")
                    return

            # 2) Session-scope protection for log channel
            if LOG_CH_ID and isinstance(getattr(ch, "id", None), int) and ch.id == LOG_CH_ID:
                created_ts = int(self.created_at.timestamp()) if getattr(self, "created_at", None) else None
                if created_ts and created_ts < STARTUP_TS:
                    log.info("[delete_safe_plus] ignore delete for pre-session log message (session-scope)")
                    return
        except Exception:
            pass
        return await orig_delete(self, *a, **kw)

    discord.Message.delete = _safe_delete
    log.info("[delete_safe_plus] Message.delete patched (pinned+keeper+session log protect)")

class DeleteSafeShimPlus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        setup_delete_guard()

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShimPlus(bot))
