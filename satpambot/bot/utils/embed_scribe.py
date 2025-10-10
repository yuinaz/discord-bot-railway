"""Helper untuk tulis/update embed keeper (pinned) dengan aman.
- Tahan error permission
- Tidak akses attribute .id saat None
- Sediakan API module-level `upsert(...)` dan class `EmbedScribe`
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any

import discord

log = logging.getLogger(__name__)

# cache mapping arbitrary key -> keeper message id (opsional)
ch_map: Dict[str, int] = {}

async def _find_keeper_message(ch: discord.TextChannel, key: str) -> Optional[discord.Message]:
    try:
        pins = await ch.pins()
    except Exception:
        pins = []
    for m in pins:
        try:
            content = m.content or ""
            if key in content:
                return m
        except Exception:
            continue
    # fallback scan kecil di 20 terakhir
    try:
        async for m in ch.history(limit=20, oldest_first=False):
            if (m.content or "").find(key) != -1:
                return m
    except Exception:
        pass
    return None

async def upsert(ch: discord.TextChannel, key: str, embed: discord.Embed, *, pin: bool = True, bot=None, route: bool = False) -> Optional[discord.Message]:
    """Upsert satu pesan 'keeper' yang mengandung `key` dan update embed-nya.
    Tidak lempar error fatal; return None jika gagal total.
    """
    keeper: Optional[discord.Message] = None
    try:
        keeper = await _find_keeper_message(ch, key)
        if keeper is None:
            # buat baru
            try:
                keeper = await ch.send(content=f"[{key}] keeper", embed=embed)
            except discord.Forbidden:
                log.warning("[embed_scribe] forbidden send to #%s", getattr(ch, 'name', ch.id))
                return None
            except Exception:
                log.exception("[embed_scribe] gagal membuat keeper")
                return None
            # pin kalau boleh
            if pin:
                try:
                    await keeper.pin(reason=f"keeper:{key}")
                except Exception:
                    # boleh gagal; jangan crash
                    log.debug("[embed_scribe] pin gagal untuk keeper %s", keeper.id if keeper else None)
        else:
            # edit existing
            try:
                await keeper.edit(content=f"[{key}] keeper", embed=embed)
            except discord.Forbidden:
                log.warning("[embed_scribe] forbidden edit in #%s", getattr(ch, 'name', ch.id))
                return None
            except Exception:
                log.exception("[embed_scribe] gagal edit keeper")
                return None

        if keeper is not None:
            try:
                ch_map[key] = int(keeper.id)
            except Exception:
                pass
        return keeper
    except Exception:
        log.exception("[embed_scribe] upsert fatal error")
        return None


class EmbedScribe:
    """Compat class API untuk import lama."""
    def __init__(self, key: str = "SATPAMBOT_KEEPER") -> None:
        self.key = key

    async def upsert(self, ch: discord.TextChannel, key: Optional[str], embed: discord.Embed, *, pin: bool = True, bot=None, route: bool = False) -> Optional[discord.Message]:
        return await upsert(ch, key or self.key, embed, pin=pin, bot=bot, route=route)
