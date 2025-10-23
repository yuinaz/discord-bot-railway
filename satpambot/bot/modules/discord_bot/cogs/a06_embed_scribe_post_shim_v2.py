
# a06_embed_scribe_post_shim_v2.py
# Minimal: ensure EmbedScribe has async upsert/post; no-op if already correct.
import logging
from discord.ext import commands
log=logging.getLogger(__name__)
def _inject():
    try:
        mod=__import__("satpambot.bot.utils.embed_scribe", fromlist=["*"])
    except Exception as e:
        log.debug("[post_shim] no embed_scribe: %r", e); return False
    ES=getattr(mod,"EmbedScribe",None)
    if ES is None: return False
    # class method: upsert
    fn=getattr(ES,"upsert",None)
    if fn and not getattr(fn,"__is_async__",False):
        async def up(*a,**k):
            res=fn(*a,**k)
            if hasattr(res,"__await__"): return await res
            return res
        up.__is_async__=True
        setattr(ES,"upsert",up); log.info("[post_shim] async-ified EmbedScribe.upsert")
    return True
class Shim(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self): _inject()
async def setup(bot): await bot.add_cog(Shim(bot))
