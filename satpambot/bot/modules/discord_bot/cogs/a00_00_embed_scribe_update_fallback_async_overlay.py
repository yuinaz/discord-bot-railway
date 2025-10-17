import inspect
from discord.ext import commands
from satpambot.bot.utils.embed_scribe import EmbedScribe

class EmbedScribeUpdateFallbackAsyncOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        for name in ("post", "update"):
            if hasattr(EmbedScribe, name):
                orig = getattr(EmbedScribe, name)
                async def wrapper(*a, __orig=orig, **kw):
                    res = __orig(*a, **kw)
                    if inspect.iscoroutine(res):
                        return await res
                    return res
                setattr(EmbedScribe, name, wrapper)

async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateFallbackAsyncOverlay(bot))
