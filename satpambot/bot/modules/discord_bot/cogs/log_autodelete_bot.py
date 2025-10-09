# -*- coding: utf-8 -*-
"""LogAutoDeleteBot v2
Auto-bersihkan pesan spam di channel log (bukan thread 'neuro-lite progress').

Fitur:
- TTL berbasis ENV `LOG_AUTODELETE_TTL_SECONDS` (default 900 = 15m).
- Hanya bekerja di channel target (`LOG_AUTODELETE_CHANNEL_ID` atau `LOG_CHANNEL_ID`).
- Hanya hapus pesan BOT dan yang TIDAK pinned.
- Pola filter opsional via ENV `LOG_AUTODELETE_PATTERNS` (comma-separated).
- De-dupe: untuk judul embed/first-line yang sama, hanya **satu** terakhir yang dibiarkan (env `LOG_AUTODELETE_KEEP_LATEST_PER_TITLE=1`).
- Tidak menyentuh pesan dalam thread 'neuro-lite progress' (proteksi).
- Integrasi dengan delete_safe_shim.allow_delete_for agar penghapusan aman.

Catatan:
- Ini membersihkan **channel log utama saja**, bukan thread progress. Memory keeper aman.
"""
from __future__ import annotations
import os, asyncio, logging, contextlib, datetime as dt
from typing import List, Dict, Optional
import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers.thread_utils import DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

def _env_list(name: str) -> List[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]

def _get_ttl() -> int:
    try:
        return int(os.getenv("LOG_AUTODELETE_TTL_SECONDS", "900"))
    except Exception:
        return 900

def _target_channel_id(bot: commands.Bot) -> Optional[int]:
    raw = os.getenv("LOG_AUTODELETE_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or ""
    try:
        cid = int(str(raw).strip())
        return cid
    except Exception:
        return None

def _is_in_neuro_thread(msg: discord.Message) -> bool:
    try:
        ch = msg.channel
        if isinstance(ch, discord.Thread):
            return (ch.name or "").strip().lower() == (DEFAULT_THREAD_NAME or "").strip().lower()
        return False
    except Exception:
        return False

def _title_or_firstline(msg: discord.Message) -> str:
    # try embed title, else first non-empty line of content
    try:
        if msg.embeds:
            e = msg.embeds[0]
            if e.title:
                return e.title
    except Exception:
        pass
    try:
        c = (msg.content or "").strip()
        if c:
            return c.splitlines()[0][:80]
    except Exception:
        pass
    return ""

def _matches_patterns(msg: discord.Message, patterns: List[str]) -> bool:
    if not patterns:
        return True
    text = ((msg.content or "") + " " + " ".join([getattr(e, "title", "") or "" for e in (msg.embeds or [])])).lower()
    return any(p.lower() in text for p in patterns)

class LogAutoDeleteBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ttl = _get_ttl()
        self._patterns = _env_list("LOG_AUTODELETE_PATTERNS")  # e.g. "Proposal:,Periodic Status,Maintenance"
        self._keep_latest = os.getenv("LOG_AUTODELETE_KEEP_LATEST_PER_TITLE", "1") not in ("0","false","False","no","No")
        self._task.start()
        log.info("[log_autodelete] start (ttl=%ss, patterns=%s, keep_latest=%s)",
                 self._ttl, self._patterns or "*", self._keep_latest)

    def cog_unload(self):
        with contextlib.suppress(Exception):
            self._task.cancel()

    async def _maybe_delete(self, msg: discord.Message):
        # Never touch neuro thread messages
        if _is_in_neuro_thread(msg):
            return
        if msg.pinned:
            return
        if not getattr(getattr(msg, "author", None), "bot", False):
            return
        if not _matches_patterns(msg, self._patterns):
            return

        # allowlist so delete_safe_shim won't block this
        try:
            from satpambot.bot.modules.discord_bot.cogs.delete_safe_shim import allow_delete_for
            allow_delete_for(int(msg.id))
        except Exception:
            pass
        with contextlib.suppress(Exception):
            await msg.delete()

    @tasks.loop(minutes=3)
    async def _task(self):
        await self.bot.wait_until_ready()
        cid = _target_channel_id(self.bot)
        if not cid:
            return
        ch = self.bot.get_channel(cid)
        if not isinstance(ch, discord.TextChannel):
            with contextlib.suppress(Exception):
                ch = await self.bot.fetch_channel(cid)
        if not isinstance(ch, discord.TextChannel):
            log.warning("[log_autodelete] cannot resolve log channel id=%s", cid)
            return

        now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
        cutoff = now - dt.timedelta(seconds=self._ttl)

        titles_latest: Dict[str, int] = {}
        if self._keep_latest:
            # pass 1: find latest per title
            async for m in ch.history(limit=200, oldest_first=False):
                if _is_in_neuro_thread(m):
                    continue  # skip thread messages
                if m.created_at < cutoff:
                    continue  # only needed for de-dupe among fresh messages
                t = _title_or_firstline(m)
                if not t:
                    continue
                titles_latest.setdefault(t, m.id)

        # pass 2: cleanup
        async for m in ch.history(limit=400, oldest_first=False):
            if _is_in_neuro_thread(m):
                continue
            # delete if older than TTL
            if m.created_at < cutoff:
                await self._maybe_delete(m)
                continue
            # if keep-latest enabled, remove prior duplicates for same title
            if self._keep_latest:
                t = _title_or_firstline(m)
                if t and titles_latest.get(t) and titles_latest[t] != m.id:
                    await self._maybe_delete(m)

async def setup(bot: commands.Bot):
    await bot.add_cog(LogAutoDeleteBot(bot))
