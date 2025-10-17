# a06_embed_scribe_update_fallback_async_overlay.py
import logging, asyncio, inspect
from discord.ext import commands

log = logging.getLogger(__name__)

class EmbedScribeUpdateFallbackAsync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        try:
            from satpambot.bot.utils import embed_scribe as m
        except Exception as e:
            log.debug("[embed-fallback-async] embed_scribe import failed: %r", e)
            return
        ES = getattr(m, "EmbedScribe", None)
        if ES is None:
            return

        orig_update = getattr(ES, "update", None)
        orig_post = getattr(ES, "post", None)

        async def _call_maybe(coro_or_val):
            if inspect.isawaitable(coro_or_val):
                return await coro_or_val
            return coro_or_val

        async def _safe_update(self, *a, **kw):
            # Try original update first
            if callable(orig_update):
                try:
                    return await _call_maybe(orig_update(self, *a, **kw))
                except Exception as ex:
                    log.debug("[embed-fallback-async] update failed: %r; falling back to post()", ex)

            # Fallback to post()
            if callable(orig_post):
                try:
                    return await _call_maybe(orig_post(self))
                except Exception as ex2:
                    log.debug("[embed-fallback-async] post() failed: %r", ex2)
                    return None
            return None

        # Only patch once
        if getattr(ES, "_update_patched_async_fallback", False):
            return
        ES.update = _safe_update
        ES._update_patched_async_fallback = True
        log.info("[embed-fallback-async] EmbedScribe.update wrapped with async-safe fallback")

async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallbackAsync(bot))
