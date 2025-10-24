from __future__ import annotations
import os, re, logging, asyncio
from typing import Optional
try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Embed: ...
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*a, **k):
                def _w(f): return f
                return _w
        @staticmethod
        def listener(*a, **k):
            def _w(f): return f
            return _w

log = logging.getLogger(__name__)

def _cfg_int(name: str, default: Optional[int]=None) -> Optional[int]:
    v = os.getenv(name, "")
    try: return int(v) if v else default
    except Exception: return default

QNA_PUBLIC_CHANNEL_ID = _cfg_int("QNA_PUBLIC_CHANNEL_ID", None)
QNA_PUBLIC_GATE = (os.getenv("QNA_PUBLIC_GATE") or "lock").lower()

_QUE = re.compile(r"\b(question|pertanyaan)\b", re.I)
_ANS = re.compile(r"\b(answer|jawaban)\b", re.I)

class QnaPublicAutoAnswer(commands.Cog):
    """Answer 'Question' embeds only in public channel AND only when gate unlock."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            if not QNA_PUBLIC_CHANNEL_ID or QNA_PUBLIC_GATE != "unlock": return
            if getattr(getattr(m,"channel",None),"id",None) != QNA_PUBLIC_CHANNEL_ID: return
            if not getattr(getattr(m,"author",None),"bot",False): return
            if not getattr(m, "embeds", None) or len(m.embeds)==0: return
            e = m.embeds[0]
            def g(x): return (x or "").strip().lower()
            text = " ".join([g(getattr(e,"title","")), g(getattr(getattr(e,"author",None),"name",None)), g(getattr(e,"description",""))])
            if _ANS.search(text): return  # ignore answers
            if not _QUE.search(text): return
            # Let your existing dual-provider runtime overlay handle the actual call via slash or other triggers.
            # This cog ensures we don't auto-answer unless gate is unlocked.
            return
        except Exception as ex:
            log.warning("[qna-public] fail: %r", ex)

async def setup(bot):
    await bot.add_cog(QnaPublicAutoAnswer(bot))
