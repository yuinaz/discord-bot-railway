from __future__ import annotations
import time
import discord
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from .env import LOG_CHANNEL_ID

# cache in-memory: (guild_id, channel_id) -> message_id
_status_msg_cache: dict[tuple[int, int], int] = {}

def _get_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    if not guild or not LOG_CHANNEL_ID:
        return None
    ch = guild.get_channel(LOG_CHANNEL_ID)
    return ch if isinstance(ch, discord.TextChannel) else None

def _now_wib_str() -> str:
    if ZoneInfo:
        dt = datetime.now(ZoneInfo("Asia/Jakarta"))
        off = dt.strftime("%z")
        off = f"{off[:3]}:{off[3:]}" if off and len(off) == 5 else "+07:00"
        return f"{dt:%Y-%m-%d %H:%M:%S} WIB ({off})"
    return time.strftime("%Y-%m-%d %H:%M:%S WIB (+07:00)", time.gmtime())

def _build_status_embed(text: str) -> discord.Embed:
    emb = discord.Embed(title="SatpamBot Status", description=text, color=discord.Color.green())
    emb.set_footer(text=f"Terakhir diperbarui: {_now_wib_str()}")
    return emb

async def _find_existing_status_message(ch: discord.TextChannel) -> discord.Message | None:
    # 1) cek PIN (cepat)
    try:
        for msg in await ch.pins():
            if msg.author == ch.guild.me and msg.embeds and (msg.embeds[0].title or "").strip() == "SatpamBot Status":
                return msg
    except Exception:
        pass
    # 2) lihat ≤10 pesan terakhir
    try:
        async for msg in ch.history(limit=10, oldest_first=False):
            if msg.author == ch.guild.me and msg.embeds and (msg.embeds[0].title or "").strip() == "SatpamBot Status":
                return msg
    except Exception:
        pass
    return None

async def upsert_status_embed_in_channel(ch: discord.TextChannel, text: str) -> bool:
    # ❗ hanya izinkan di channel ID yang benar
    if not isinstance(ch, discord.TextChannel) or not LOG_CHANNEL_ID or ch.id != LOG_CHANNEL_ID:
        return False

    key = (ch.guild.id if ch.guild else 0, ch.id)
    emb = _build_status_embed(text)

    # 0) pakai cache kalau ada
    mid = _status_msg_cache.get(key)
    if mid:
        try:
            msg = await ch.fetch_message(mid)
            await msg.edit(embed=emb)
            return True
        except Exception:
            pass

    # 1) cari pesan lama (PIN/riwayat pendek)
    msg = await _find_existing_status_message(ch)
    if msg:
        try:
            await msg.edit(embed=emb)
            _status_msg_cache[key] = msg.id
            return True
        except Exception:
            pass

    # 2) buat baru + auto-pin (sekali)
    try:
        msg = await ch.send(embed=emb)
        _status_msg_cache[key] = msg.id
        try:
            await msg.pin(reason="Sticky SatpamBot status")
        except Exception:
            pass
        return True
    except Exception:
        return False

async def upsert_status_embed(guild: discord.Guild, text: str) -> bool:
    ch = _get_log_channel(guild)
    return await upsert_status_embed_in_channel(ch, text) if ch else False

async def announce_bot_online(guild: discord.Guild, bot_tag: str):
    # tidak ada fallback—kalau channel tidak ada/terlihat, skip saja
    try:
        await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.")
    except Exception:
        pass
