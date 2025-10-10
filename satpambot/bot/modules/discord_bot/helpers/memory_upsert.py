import logging
from typing import Any, Dict

import discord

from satpambot.bot.utils import embed_scribe

log = logging.getLogger(__name__)

async def upsert_pinned_memory(bot, payload: Dict[str, Any]) -> bool:
    """Buat/update keeper embed 'SATPAMBOT_PINNED_MEMORY'. Aman kalau gagal permission."""
    try:
        ch_id = int(payload.get("channel_id"))
    except Exception:
        log.warning("[memory_upsert] payload tidak valid: %s", payload)
        return False

    ch = bot.get_channel(ch_id)
    if ch is None:
        try:
            ch = await bot.fetch_channel(ch_id)
        except Exception:
            log.warning("[memory_upsert] channel %s tidak ditemukan", ch_id)
            return False

    e = payload.get("embed")
    if not isinstance(e, discord.Embed):
        # build embed kalau payload bawa dict
        try:
            data = payload.get("embed_data") or {}
            e = discord.Embed.from_dict(data) if data else discord.Embed(title="Memory")
        except Exception:
            e = discord.Embed(title="Memory")

    keeper = await embed_scribe.upsert(ch, "SATPAMBOT_PINNED_MEMORY", e, pin=True, bot=bot, route=True)
    if keeper is None:
        log.info("[memory_upsert] keeper None (kemungkinan no permission); skip tanpa error")
        return False
    return True
