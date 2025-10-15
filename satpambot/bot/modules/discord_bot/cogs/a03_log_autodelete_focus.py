
import asyncio
import logging
import re
from typing import Optional

import discord

log = logging.getLogger(__name__)

# === CONFIG (no ENV) ===
TTL_DEFAULT = 180  # detik

TTL_BY_PATTERN = [
    (re.compile(r"^Self-?Heal Ticket\b", re.I), 12),
    (re.compile(r"\bSelfHealRuntime aktif\b", re.I), 12),
    (re.compile(r"\bAuto reseed", re.I), 15),
    (re.compile(r"\bAuto reseed selesai\b", re.I), 15),
    (re.compile(r"\bsetup failed: Cog named 'SelfHealAutoFix' already loaded\b", re.I), 12),
]

PROTECT_PINNED = True
_PATCHED = False

async def _safe_autodelete(msg: discord.Message, ttl: int) -> None:
    if ttl <= 0:
        return
    try:
        await asyncio.sleep(ttl)
        if PROTECT_PINNED:
            try:
                if hasattr(msg, "channel"):
                    msg = await msg.channel.fetch_message(msg.id)
            except Exception:
                pass
            if getattr(msg, "pinned", False):
                return
        await msg.delete()
    except (discord.NotFound, discord.Forbidden):
        pass
    except Exception:
        log.exception("[log_autodelete] gagal menghapus pesan")

def _match_ttl_from_message(content: str, embeds: list) -> Optional[int]:
    text_blobs = [content or ""]
    for e in embeds or []:
        if isinstance(e, discord.Embed):
            if e.title:
                text_blobs.append(e.title)
            if e.description:
                text_blobs.append(e.description[:300])
            for f in e.fields:
                text_blobs.append((f.name or "")[:120])
    blob = "\n".join(text_blobs)
    for rx, ttl in TTL_BY_PATTERN:
        if rx.search(blob):
            return ttl
    return None

async def _wrapped_send(self, *args, **kwargs):
    msg = await _wrapped_send.__orig(self, *args, **kwargs)
    try:
        channel_id = getattr(self, "id", None)
        if channel_id is None and hasattr(self, "channel"):
            channel_id = getattr(self.channel, "id", None)

        target = channel_id in LOG_CHANNEL_IDS or channel_id in PROGRESS_THREAD_IDS
        if not target:
            return msg

        if not getattr(msg.author, "bot", False):
            return msg

        ttl = _match_ttl_from_message(getattr(msg, "content", "") or "", getattr(msg, "embeds", []) or [])
        if ttl is None:
            ttl = TTL_DEFAULT

        if ttl and ttl > 0:
            asyncio.create_task(_safe_autodelete(msg, ttl))

    except Exception:
        log.exception("[log_autodelete] wrapper error")

    return msg

async def setup(bot):
    global _PATCHED
    if _PATCHED:
        log.info("[log_autodelete] already patched; skip")
        return

    orig_send = discord.abc.Messageable.send
    if getattr(orig_send, "__name__", "") != "_wrapped_send":
        _wrapped_send.__orig = orig_send  # type: ignore[attr-defined]
        discord.abc.Messageable.send = _wrapped_send  # type: ignore[assignment]
        _PATCHED = True
        log.info("[log_autodelete] patched Messageable.send — LOG_CHANNEL_IDS=%s PROGRESS_THREAD_IDS=%s", LOG_CHANNEL_IDS, PROGRESS_THREAD_IDS)
    else:
        log.info("[log_autodelete] Messageable.send sudah ter-wrap")

def setup_sync(bot):
    return asyncio.get_event_loop().create_task(setup(bot))

# patched: force LOG_CHANNEL_IDS at module top-level (outside try/except)
LOG_CHANNEL_IDS = {1400375184048787566}

# patched: force PROGRESS_THREAD_IDS at module top-level (outside try/except)
PROGRESS_THREAD_IDS = {1422624261109190716, 1426397317598154844, 1425400701982478408, 1409949797313679492}
