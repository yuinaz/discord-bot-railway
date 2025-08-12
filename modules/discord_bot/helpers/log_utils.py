from __future__ import annotations
import time
import discord
from datetime import datetime
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except Exception:
    ZoneInfo = None

from .env import LOG_CHANNEL_ID, LOG_CHANNEL_NAME

# Cache in-memory: (guild_id, channel_id) -> message_id
_status_msg_cache: dict[tuple[int, int], int] = {}

def _find_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Prioritas ID, lalu nama channel (fallback)."""
    if not guild:
        return None
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    names = {LOG_CHANNEL_NAME, "lot-botphising", "log-botphishing"}
    for ch in guild.text_channels:
        if ch.name in names:
            return ch
    return None

def _now_wib_str() -> str:
    if ZoneInfo:
        dt = datetime.now(ZoneInfo("Asia/Jakarta"))
        off = dt.strftime("%z")  # "+0700"
        off = f"{off[:3]}:{off[3:]}" if off and len(off) == 5 else "+07:00"
        return f"{dt:%Y-%m-%d %H:%M:%S} WIB ({off})"
    # Fallback tanpa zoneinfo
    return time.strftime("%Y-%m-%d %H:%M:%S WIB (+07:00)", time.gmtime())

def _build_status_embed(text: str) -> discord.Embed:
    emb = discord.Embed(
        title="SatpamBot Status",
        description=text,
        color=discord.Color.green(),
    )
    emb.set_footer(text=f"Terakhir diperbarui: {_now_wib_str()}")
    return emb

async def _find_existing_status_message(ch: discord.TextChannel) -> discord.Message | None:
    """Cari pesan status lewat PIN lebih dulu (paling ringan), lalu ≤10 pesan terakhir."""
    # 1) Cari di PIN
    try:
        pins = await ch.pins()
        for msg in pins:
            if msg.author == ch.guild.me and msg.embeds:
                e = msg.embeds[0]
                if (e.title or "").strip() == "SatpamBot Status":
                    return msg
    except Exception:
        pass
    # 2) Terakhir, lihat ≤10 pesan terakhir
    try:
        async for msg in ch.history(limit=10, oldest_first=False):
            if msg.author == ch.guild.me and msg.embeds:
                e = msg.embeds[0]
                if (e.title or "").strip() == "SatpamBot Status":
                    return msg
    except Exception:
        pass
    return None

async def upsert_status_embed_in_channel(ch: discord.TextChannel, text: str) -> bool:
    """Edit embed status kalau ada; kalau belum, cari cepat; terakhir, buat baru & auto-pin."""
    if not isinstance(ch, discord.TextChannel):
        return False

    # 🔒 Guard: hanya izinkan update di channel log yang benar
    if LOG_CHANNEL_ID and getattr(ch, "id", None) != LOG_CHANNEL_ID:
        return False

    key = (ch.guild.id if ch.guild else 0, ch.id)
    emb = _build_status_embed(text)

    # 0) Coba dari cache
    mid = _status_msg_cache.get(key)
    if mid:
        try:
            msg = await ch.fetch_message(mid)
            await msg.edit(embed=emb)
            return True
        except Exception:
            pass  # cache miss → lanjut cari

    # 1) Cari existing via PIN/riwayat pendek
    msg = await _find_existing_status_message(ch)
    if msg:
        try:
            await msg.edit(embed=emb)
            _status_msg_cache[key] = msg.id
            return True
        except Exception:
            pass

    # 2) Buat baru (sekali), lalu auto-pin supaya next time super cepat
    try:
        msg = await ch.send(embed=emb)
        _status_msg_cache[key] = msg.id
        try:
            await msg.pin(reason="Sticky SatpamBot status")
        except Exception:
            pass  # kalau gak bisa pin, tidak apa-apa
        return True
    except Exception:
        return False

async def upsert_status_embed(guild: discord.Guild, text: str) -> bool:
    ch = _find_log_channel(guild)
    if not ch:
        return False
    return await upsert_status_embed_in_channel(ch, text)

async def announce_bot_online(guild: discord.Guild, bot_tag: str):
    """Kompatibel dengan pemanggil lama—gunakan upsert supaya sticky."""
    try:
        await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.")
    except Exception:
        ch = _find_log_channel(guild)
        if ch:
            try:
                await ch.send("✅ SatpamBot online dan siap berjaga.")
            except Exception:
                pass
