import inspect
from discord.ext import commands
try:
    from satpambot.bot.utils.embed_scribe import EmbedScribe
except Exception:
    EmbedScribe = None

class EmbedScribeUpdateFallbackAsyncOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if EmbedScribe and not getattr(EmbedScribe, "_leina_safe_update_patched", False):
            original = getattr(EmbedScribe, "update", None)
            if original is not None:
                def safe_update(self, *args, **kwargs):
                    res = original(self, *args, **kwargs)
                    if inspect.isawaitable(res):
                        return res
                    async def _noop():
                        return res
                    return _noop()
                EmbedScribe.update = safe_update
                EmbedScribe._leina_safe_update_patched = True

async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallbackAsyncOverlay(bot))
