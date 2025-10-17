import logging, inspect
from discord.ext import commands

log = logging.getLogger(__name__)

class EmbedScribeAwaitFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            from satpambot.bot.utils import embed_scribe as es
            if hasattr(es, "EmbedScribe") and hasattr(es.EmbedScribe, "update"):
                orig = es.EmbedScribe.update
                async def safe_update(self, *a, **k):
                    try:
                        res = orig(self, *a, **k)
                        if inspect.isawaitable(res):
                            return await res
                        return res
                    except Exception as e:
                        log.warning("[embed-fix] update fallback: %s", e)
                        return None
                es.EmbedScribe.update = safe_update
                log.info("[embed-fix] EmbedScribe.update patched")
        except Exception as e:
            log.warning("[embed-fix] patch failed: %s", e)

async def setup(bot):
    await bot.add_cog(EmbedScribeAwaitFix(bot))
