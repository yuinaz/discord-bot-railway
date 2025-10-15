
import asyncio
import logging
import re
import discord

log = logging.getLogger(__name__)

LOG_CHANNEL_IDS = {1400375184048787566}
TTL_TICKET = 12

async def _safe_delete(msg: discord.Message, ttl: int):
    try:
        await asyncio.sleep(ttl)
        await msg.delete()
    except Exception:
        pass

async def setup(bot):
    try:
        from satpambot.bot.modules.discord_bot.cogs import selfheal_router as _router
    except Exception:
        log.warning("[selfheal_embed_overlay] selfheal_router tidak ditemukan; skip")
        return

    cls = getattr(_router, "SelfHealRouter", None)
    if cls is None:
        log.warning("[selfheal_embed_overlay] SelfHealRouter tidak tersedia; skip")
        return

    if hasattr(cls, "_post"):
        orig = cls._post
        async def _wrapped(self, *a, **kw):
            msg = await orig(self, *a, **kw)
            try:
                ch_id = getattr(getattr(msg, "channel", None), "id", None)
                if ch_id in LOG_CHANNEL_IDS:
                    title = ""
                    if msg and msg.embeds:
                        e = msg.embeds[0]
                        title = (e.title or "") if isinstance(e, discord.Embed) else ""
                    if re.search(r"^Self-?Heal Ticket\b", title, re.I):
                        asyncio.create_task(_safe_delete(msg, TTL_TICKET))
            except Exception:
                pass
            return msg
        cls._post = _wrapped
        log.info("[selfheal_embed_overlay] patched SelfHealRouter._post (TTL=%s)", TTL_TICKET)
    else:
        log.info("[selfheal_embed_overlay] SelfHealRouter._post tidak ada; skip")
