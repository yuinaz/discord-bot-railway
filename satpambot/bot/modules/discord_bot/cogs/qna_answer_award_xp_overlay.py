try:
    import discord
    from discord.ext import commands
except Exception:
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

from .....config.auto_defaults import cfg_int, cfg_str
import logging, re
log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

_ANS_PROVIDER = re.compile(r"\banswer\s+by\s+(groq|gemini)\b", re.I)
_QUE_PAT = re.compile(r"\b(question|pertanyaan)\b", re.I)

def _is_provider_answer_embed(e: "discord.Embed") -> bool:
    def g(x): return (x or "").strip().lower()
    title = g(getattr(e, "title",""))
    author = g(getattr(getattr(e,"author",None),"name",None))
    desc = g(getattr(e,"description",""))
    foot = g(getattr(getattr(e,"footer",None),"text",None))
    hay = " ".join([title, author, desc, foot])
    if _QUE_PAT.search(hay):  # safeguard
        return False
    if "qna_provider:" in foot:
        return any(p in foot for p in ["groq","gemini"])
    return _ANS_PROVIDER.search(hay) is not None

class QnaAnswerAwardXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna_id = cfg_int("QNA_CHANNEL_ID", 0) or None
        self.client = UpstashClient() if UpstashClient else None
        self.delta = int(cfg_str("QNA_XP_PER_ANSWER_BOT", "5") or "5")
        self.senior_key = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")
        self.ns = cfg_str("QNA_AWARD_IDEMP_NS", "qna:awarded:answer")

    async def _mark_once(self, mid: int) -> bool:
        if not self.client or not getattr(self.client, "enabled", False):
            return False
        key = f"{self.ns}:{int(mid)}"
        try:
            if await self.client.get_raw(key) is not None:
                return False
            await self.client.setex(key, 60*60*24*90, "1")
            return True
        except Exception:
            return False

    @commands.Cog.listener()
    async def on_message(self, m: "discord.Message"):
        try:
            if self.qna_id and getattr(getattr(m,"channel",None),"id",None) != self.qna_id: return
            if not getattr(getattr(m,"author",None),"bot",False): return
            if not getattr(m, "embeds", None): return
            if len(m.embeds) == 0: return
            e = m.embeds[0]
            if not _is_provider_answer_embed(e): return
            if not await self._mark_once(int(m.id)): return
            if not self.client or not getattr(self.client, "enabled", False): return
            await self.client.incrby(self.senior_key, int(self.delta))
            log.info("[qna-award] +%s XP (provider-answer) key=%s msg=%s", self.delta, self.senior_key, m.id)
        except Exception as exc:
            log.warning("[qna-award] failed: %r", exc)

async def setup(bot): await bot.add_cog(QnaAnswerAwardXP(bot))
