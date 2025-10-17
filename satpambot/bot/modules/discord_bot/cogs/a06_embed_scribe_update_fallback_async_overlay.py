# Ensure EmbedScribe.update doesn't await None
from discord.ext import commands
import types

class EmbedScribeUpdateFallback(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot
        self._patch()

    def _patch(self):
        try:
            from ...utils.embed_scribe import EmbedScribe
        except Exception:
            return
        orig_update = getattr(EmbedScribe, "update", None)
        if not orig_update: 
            return
        async def safe_update(self, *a, **kw):
            try:
                r = await orig_update(self, *a, **kw)
                return r
            except TypeError as e:
                # "object NoneType can't be used in 'await' expression"
                return None
        setattr(EmbedScribe, "update", safe_update)

async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallback(bot))
