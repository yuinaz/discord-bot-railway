
# a08_xp_upstash_exact_keys_overlay.py (v7.1 replacement)
# Minimal, import-safe stub to prevent TypeError from wrong listener signature.
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
class UpstashExactKeysOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        # Swallow / normalize event to avoid "takes 2 positional args but 4/6 given"
        try:
            # Keep as lightweight logger; real persistence handled by sink overlay
            log.info("[xp-upstash:exact-keys] event normalized: args=%s kwargs=%s", str(args)[:200], str(kwargs)[:200])
        except Exception as e:
            log.info("[xp-upstash:exact-keys] handler error: %r", e)
async def setup(bot):
    try: await bot.add_cog(UpstashExactKeysOverlay(bot))
    except Exception as e: log.info("[xp-upstash:exact-keys] setup swallowed: %r", e)
