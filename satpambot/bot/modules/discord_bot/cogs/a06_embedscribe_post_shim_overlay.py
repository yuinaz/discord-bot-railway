
"""
a06_embedscribe_post_shim_overlay.py
- Some builds expect EmbedScribe.post(). Older compat exposes _post().
- This overlay tries to alias .post to existing ._post or .send to avoid AttributeError.
"""
import logging, types
from discord.ext import commands

log = logging.getLogger(__name__)

def _patch():
    try:
        import satpambot.bot.modules.discord_bot.cogs.embed_scribe_compat as m
    except Exception:
        try:
            import satpambot.bot.modules.discord_bot.cogs.embed_scribe as m  # best effort
        except Exception:
            m = None
    if not m: 
        return 0
    count = 0
    for name in dir(m):
        obj = getattr(m, name, None)
        if hasattr(obj, "__name__") and "EmbedScribe" in obj.__name__:
            try:
                if getattr(obj, "post", None) is None:
                    if getattr(obj, "_post", None):
                        obj.post = obj._post
                        count += 1
                    elif getattr(obj, "send", None):
                        obj.post = obj.send
                        count += 1
            except Exception:
                pass
    return count

class EmbedScribePostShim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        n = _patch()
        if n:
            log.info("[embed-post-shim] patched %d class(es)", n)

async def setup(bot):
    await bot.add_cog(EmbedScribePostShim(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(EmbedScribePostShim(bot)))
    except Exception:
        pass
    return bot.add_cog(EmbedScribePostShim(bot))
