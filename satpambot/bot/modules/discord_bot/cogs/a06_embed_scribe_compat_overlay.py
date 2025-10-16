
# a06_embed_scribe_compat_overlay.py (v7.4)
import sys, logging
from discord.ext import commands
log = logging.getLogger(__name__)
def _patch_embed_scribe():
    try:
        for name, mod in list(sys.modules.items()):
            if not name or "embed" not in name: continue
            cls = getattr(mod, "EmbedScribe", None)
            if cls and not hasattr(cls, "post"):
                def post(self, *a, **k):
                    if hasattr(self, "upsert"): return self.upsert(*a, **k)
                    if hasattr(self, "write"):  return self.write(*a, **k)
                    return None
                setattr(cls, "post", post)
                log.info("[scribe-compat] Injected EmbedScribe.post alias")
    except Exception as e: log.info("[scribe-compat] patch failed: %r", e)
class EmbedScribeCompat(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self): _patch_embed_scribe()
async def setup(bot):
    try: await bot.add_cog(EmbedScribeCompat(bot))
    except Exception as e: log.info("[scribe-compat] setup swallowed: %r", e)
