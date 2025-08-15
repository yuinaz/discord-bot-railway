# modules/discord_bot/helpers/log_utils.py
from __future__ import annotations

import os
import discord
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Tuple

# ---- env bindings (robust) ----
try:
    from .env import LOG_CHANNEL_ID  # type: ignore
except Exception:
    LOG_CHANNEL_ID = None  # type: ignore[assignment]

# Optional name-based resolution if available
try:
    from .env import LOG_CHANNEL_NAME, resolve_log_channel  # type: ignore
except Exception:
    LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "")  # type: ignore
    resolve_log_channel = None  # type: ignore

# ---- zoneinfo/pytz WIB helper ----
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError  # Python 3.9+
except Exception:  # pragma: no cover - older envs
    ZoneInfo, ZoneInfoNotFoundError = None, Exception  # type: ignore

def _wib_tz():
    """Return a tzinfo for Asia/Jakarta with robust fallbacks.
    Order:
      1) zoneinfo (IANA) — tries again after importing tzdata if missing
      2) pytz — if installed
      3) fixed-offset UTC+7 (no DST)
    """
    # 1) zoneinfo
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Jakarta")
        except ZoneInfoNotFoundError:
            # Try to import tzdata on Windows/dev boxes
            try:
                import tzdata  # noqa: F401
                return ZoneInfo("Asia/Jakarta")
            except Exception:
                pass
    # 2) pytz fallback
    try:
        import pytz  # type: ignore
        return pytz.timezone("Asia/Jakarta")  # type: ignore
    except Exception:
        # 3) final fallback: fixed offset UTC+7
        return timezone(timedelta(hours=7))

def _now_wib_str() -> str:
    """Formatted local time string for WIB."""
    dt = datetime.now(_wib_tz())
    # "+0700" -> "+07:00"
    off = dt.strftime("%z")
    off = f"{off[:3]}:{off[3:]}" if off and len(off) == 5 else "+07:00"
    return f"{dt:%Y-%m-%d %H:%M:%S} WIB ({off})"

# ---- status embed helpers ----
_STATUS_TITLE = "SatpamBot Status"

def _build_status_embed(text: str) -> discord.Embed:
    emb = discord.Embed(
        title=_STATUS_TITLE,
        description=text or "—",
        color=discord.Color.green(),
        timestamp=datetime.utcnow(),  # Discord render in client TZ
    )
    emb.set_footer(text=f"Terakhir diperbarui: {_now_wib_str()}")
    return emb

# cache in-memory: (guild_id, channel_id) -> message_id
_status_msg_cache: Dict[Tuple[int, int], int] = {}

def _get_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Resolve log channel using ID first, then name (if available)."""
    if guild is None:
        return None
    # 1) By ID (preferred)
    try:
        if LOG_CHANNEL_ID:
            ch = guild.get_channel(int(LOG_CHANNEL_ID))  # type: ignore[arg-type]
            if isinstance(ch, discord.TextChannel):
                return ch
    except Exception:
        pass
    # 2) resolve via helper if provided by env.py
    try:
        if resolve_log_channel:
            ch2 = guild.get_channel(int(LOG_CHANNEL_ID)) if LOG_CHANNEL_ID else None  # quick get
            if ch2:
                return ch2
            coro = resolve_log_channel(guild)  # type: ignore
            if coro:
                # handle both sync/async helper
                if hasattr(coro, "__await__"):
                    import asyncio
                    ch3 = asyncio.get_event_loop().run_until_complete(coro)
                else:
                    ch3 = coro  # type: ignore
                if isinstance(ch3, discord.TextChannel):
                    return ch3
    except Exception:
        pass
    # 3) By name env
    name = (LOG_CHANNEL_NAME or "").lstrip("#").strip()
    if name:
        for ch in guild.text_channels:
            if ch.name == name:
                return ch
    return None

async def _find_existing_status_message(ch: discord.TextChannel) -> Optional[discord.Message]:
    """Try cache first, then scan recent messages for our status embed."""
    try:
        key = (ch.guild.id, ch.id)
        mid = _status_msg_cache.get(key)
        if mid:
            try:
                msg = await ch.fetch_message(mid)
                if msg and msg.author == ch.guild.me:
                    if msg.embeds and (msg.embeds[0].title or "").strip() == _STATUS_TITLE:
                        return msg
            except Exception:
                pass
        # Fallback: scan recent few messages only (cheap)
        async for msg in ch.history(limit=10, oldest_first=False):
            if msg.author == ch.guild.me and msg.embeds and (msg.embeds[0].title or "").strip() == _STATUS_TITLE:
                _status_msg_cache[key] = msg.id
                return msg
    except Exception:
        pass
    return None

async def upsert_status_embed_in_channel(ch: discord.TextChannel, text: str) -> bool:
    """Create or update the status embed message in the given channel."""
    if not isinstance(ch, discord.TextChannel):
        return False
    # If an explicit LOG_CHANNEL_ID is configured, enforce it
    try:
        if LOG_CHANNEL_ID and int(LOG_CHANNEL_ID) != int(ch.id):  # type: ignore[arg-type]
            return False
    except Exception:
        pass

    emb = _build_status_embed(text)

    try:
        existing = await _find_existing_status_message(ch)
        if existing:
            await existing.edit(embed=emb)
            return True
        else:
            msg = await ch.send(embed=emb)
            _status_msg_cache[(ch.guild.id, ch.id)] = msg.id
            return True
    except discord.Forbidden:
        # Missing permission to send/edit in channel
        return False
    except Exception:
        return False

async def upsert_status_embed(guild: discord.Guild, text: str) -> bool:
    """Resolve the log channel in the guild and upsert the status embed."""
    ch = _get_log_channel(guild)
    return await upsert_status_embed_in_channel(ch, text) if ch else False

async def announce_bot_online(guild: discord.Guild, bot_tag: str):
    """Convenience notifier when the bot becomes ready."""
    try:
        await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.")
    except Exception:
        # Best-effort only; don't crash on startup
        pass
