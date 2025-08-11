# modules/discord_bot/helpers/log_utils.py
from __future__ import annotations

import os
import json
import time
import asyncio
from typing import Optional, Tuple

import discord
import pytz
from datetime import datetime

# ========= Konfigurasi =========
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or "0")

# Cache persistent agar tidak spam bikin pesan baru
_STATUS_CACHE_FILE = os.getenv("STATUS_MSG_CACHE_FILE", "data/status_message_ids.json")
_MIN_UPDATE_SEC = int(os.getenv("STATUS_MSG_MIN_UPDATE_SEC", "300"))  # 5 menit

# Zona waktu lokal (WIB) — bisa dioverride lewat env STATUS_TZ
TZ = pytz.timezone(os.getenv("STATUS_TZ", "Asia/Jakarta"))

# Memori cache: {(guild_id, channel_id): {"message_id": int, "ts": float}}
_status_cache: dict[Tuple[int, int], dict] = {}

# ========= Util cache =========
def _load_cache() -> None:
    global _status_cache
    try:
        if os.path.exists(_STATUS_CACHE_FILE):
            with open(_STATUS_CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            _status_cache = {(int(k.split(":")[0]), int(k.split(":")[1])): v for k, v in raw.items()}
        else:
            _status_cache = {}
    except Exception:
        _status_cache = {}

def _save_cache() -> None:
    try:
        os.makedirs(os.path.dirname(_STATUS_CACHE_FILE) or ".", exist_ok=True)
        data = {f"{g}:{c}": v for (g, c), v in _status_cache.items()}
        with open(_STATUS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

# ========= Channel resolver =========
def _find_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if not guild:
        return None
    # Prefer ID eksplisit
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    # Fallback pakai nama (beberapa variasi typo)
    names = {LOG_CHANNEL_NAME, "log-botphishing", "lot-botphising"}
    for ch in guild.text_channels:
        try:
            if ch.name in names:
                return ch
        except Exception:
            continue
    return None

# ========= Waktu WIB =========
def _now_wib_str() -> str:
    # Contoh: 2025-08-11 20:44:24 WIB (+07:00)
    dt = datetime.now(TZ)
    z = dt.strftime("%z")  # e.g. +0700
    return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} WIB ({z[:3]}:{z[3:]})"

# ========= Builder embed status (pakai WIB di footer) =========
def _build_status_embed(text: str) -> discord.Embed:
    emb = discord.Embed(
        title="SatpamBot Status",
        description=text,
        color=discord.Color.green(),
    )
    emb.set_footer(text=f"Terakhir diperbarui: {_now_wib_str()}")
    return emb

# ========= Upsert status (EDIT pesan lama, anti-spam) =========
async def upsert_status_embed_in_channel(
    channel: discord.TextChannel,
    text: str,
    *,
    force: bool = False
) -> bool:
    """
    Edit pesan status yang sudah ada, atau buat satu jika belum ada.
    Rate-limited via _MIN_UPDATE_SEC kecuali force=True.
    """
    if not channel:
        return False

    # Muat cache saat pertama kali
    if not _status_cache:
        _load_cache()

    key = (channel.guild.id if channel.guild else 0, channel.id)
    now = time.time()
    entry = _status_cache.get(key)

    # Hormati rate limit: kalau belum lewat, cukup edit ringan (biar timestamp footer update)
    if entry and not force:
        last = float(entry.get("ts") or 0)
        if now - last < _MIN_UPDATE_SEC:
            try:
                msg = await channel.fetch_message(int(entry["message_id"]))
                await msg.edit(embed=_build_status_embed(text))
                _status_cache[key] = {"message_id": msg.id, "ts": now}
                _save_cache()
                return True
            except Exception:
                # kalau gagal fetch, lanjut ke alur normal di bawah
                pass

    # Coba edit pesan yang sudah tercatat
    if entry:
        try:
            msg = await channel.fetch_message(int(entry["message_id"]))
            await msg.edit(embed=_build_status_embed(text))
            _status_cache[key] = {"message_id": msg.id, "ts": now}
            _save_cache()
            return True
        except Exception:
            # jatuh ke pencarian pesan lama
            pass

    # Cari pesan status lama oleh bot (judul sama) untuk di-reuse
    try:
        async for m in channel.history(limit=25):
            if m.author.bot and m.embeds:
                e = m.embeds[0]
                if (e.title or "").strip().lower() == "satpambot status":
                    try:
                        await m.edit(embed=_build_status_embed(text))
                        _status_cache[key] = {"message_id": m.id, "ts": now}
                        _save_cache()
                        return True
                    except Exception:
                        break
    except Exception:
        pass

    # Buat pesan baru (sekali saja)
    try:
        msg = await channel.send(embed=_build_status_embed(text))
        _status_cache[key] = {"message_id": msg.id, "ts": now}
        _save_cache()
        return True
    except Exception:
        return False

async def upsert_status_embed(
    guild: discord.Guild,
    text: str,
    *,
    force: bool = False
) -> bool:
    ch = _find_log_channel(guild)
    if not ch:
        return False
    return await upsert_status_embed_in_channel(ch, text, force=force)

# ========= Helper untuk event online =========
async def announce_bot_online(guild: discord.Guild, bot_tag: str):
    try:
        await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.", force=False)
    except Exception:
        ch = _find_log_channel(guild)
        if ch:
            try:
                await ch.send("✅ SatpamBot online dan siap berjaga.")
            except Exception:
                pass

# ========= (Opsional) Utility kirim embed log umum (pakai WIB) =========
async def send_embed_log(
    channel: discord.TextChannel,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blue()
):
    emb = discord.Embed(title=title, description=description, color=color)
    emb.set_footer(text=_now_wib_str())
    await channel.send(embed=emb)
