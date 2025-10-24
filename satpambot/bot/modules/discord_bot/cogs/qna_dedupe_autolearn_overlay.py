
try:
    import discord
    from discord.ext import commands
except Exception:  # allow smoke without discord installed
    class discord:  # type: ignore
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*args, **kwargs):
                def _wrap(fn): return fn
                return _wrap
        @staticmethod
        def listener(*args, **kwargs):
            def _wrap(fn): return fn
            return _wrap

from .....config.auto_defaults import cfg_int, cfg_bool, cfg_int as _cfg_int
import asyncio, logging
log = logging.getLogger(__name__)

class QnaDedupeAutolearnOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna_id = cfg_int("QNA_CHANNEL_ID", 0) or None
        self.enabled = cfg_bool("AUTOLEARN_DEDUP_ENABLED", True)
        self.delay_ms = _cfg_int("AUTOLEARN_DEDUP_DELETE_DELAY_MS", 900)

    @commands.Cog.listener()
    async def on_message(self, m):
        if not self.enabled: return
        if self.qna_id and getattr(getattr(m,"channel",None),"id",None) != self.qna_id: return
        if not getattr(getattr(m,"author",None),"bot",False): return
        if getattr(m,"embeds",None):
            if len(m.embeds) > 0: return
        content = (getattr(m,"content","") or "").strip()
        if not content: return
        await asyncio.sleep(max(0, self.delay_ms)/1000.0)
        try:
            await m.delete()
            log.info("[qna-dedupe] deleted non-embed message id=%s", getattr(m,"id",None))
        except Exception:
            pass

async def setup(bot): await bot.add_cog(QnaDedupeAutolearnOverlay(bot))