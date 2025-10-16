# a06_embed_scribe_post_shim_v2.py
# Target: satpambot.bot.utils.embed_scribe. Ensures class EmbedScribe has .post() and .upsert()
# so cogs like progress_embed_solo and a06_embed_scribe_compat_overlay won't error.
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

def _inject_shim(mod):
    ES = getattr(mod, "EmbedScribe", None)
    if ES is None:
        log.warning("[post_shim] EmbedScribe class not found in %s", getattr(mod, "__name__", mod))
        return False

    # Ensure .post exists (async), delegate to module-level upsert()/write_embed()/coalesce_send() if available.
    if not hasattr(ES, "post"):
        async def _post(self, *args, **kwargs):
            # Prefer exported coroutine 'upsert'
            up = getattr(mod, "upsert", None)
            if callable(up):
                return await up(*args, **kwargs)
            # Fallbacks for older helpers
            we = getattr(mod, "write_embed", None)
            if callable(we):
                return await we(*args, **kwargs)
            cs = getattr(mod, "coalesce_send", None)
            if callable(cs):
                return await cs(*args, **kwargs)
            # Last resort: no-op
            return None
        setattr(ES, "post", _post)
        log.info("[post_shim] Injected EmbedScribe.post() -> delegates to module functions")
    else:
        log.info("[post_shim] EmbedScribe.post() already exists")

    # Ensure .upsert exists on the class too (even if module-level exists)
    if not hasattr(ES, "upsert"):
        async def _upsert(self, *args, **kwargs):
            up = getattr(mod, "upsert", None)
            if callable(up):
                return await up(*args, **kwargs)
            return await self.post(*args, **kwargs)  # will no-op if needed
        setattr(ES, "upsert", _upsert)
        log.info("[post_shim] Injected EmbedScribe.upsert()")
    return True

class EmbedScribePostShim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Try the canonical path
        tried = 0
        for mod_name in (
            "satpambot.bot.utils.embed_scribe",
            "modules.discord_bot.helpers.embed_scribe",
        ):
            try:
                mod = __import__(mod_name, fromlist=["*"])
                if _inject_shim(mod):
                    tried += 1
            except Exception as e:
                log.debug("[post_shim] import failed %s: %r", mod_name, e)
        if tried == 0:
            log.warning("[post_shim] No EmbedScribe module patched")

async def setup(bot):
    await bot.add_cog(EmbedScribePostShim(bot))
