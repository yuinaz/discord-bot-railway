
import logging, re
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.auto_defaults import cfg_str, cfg_int
from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient

log = logging.getLogger(__name__)
_ANS_PROVIDER = re.compile(r"\banswer\s+by\s+(groq|gemini)\b", re.I)
_QUE_PAT = re.compile(r"\b(question|pertanyaan)\b", re.I)

def _is_provider_answer_embed(e):
    def g(x): return (x or "").strip().lower()
    title = g(getattr(e, "title",""))
    author = g(getattr(getattr(e,"author",None),"name",None))
    desc = g(getattr(e,"description",""))
    foot = g(getattr(getattr(e,"footer",None),"text",None))
    hay = " ".join([title, author, desc, foot])
    if _QUE_PAT.search(hay): return False
    return bool(_ANS_PROVIDER.search(hay))

class QnaAnswerAwardXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = UpstashClient()
        self.qna_id = cfg_int("QNA_CHANNEL_ID", 0) or cfg_int("LEARNING_QNA_CHANNEL_ID", 0) or None
        self.delta = int(cfg_str("QNA_XP_PER_ANSWER_BOT", "5") or "5")
        self.senior_key = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")

    @commands.Cog.listener("on_message")
    async def _on_message(self, m):
        try:
            if self.qna_id and getattr(getattr(m,"channel",None),"id",None) != self.qna_id: return
            if not getattr(getattr(m,"author",None),"bot",False): return
            if not getattr(m, "embeds", None): return
            if len(m.embeds) == 0: return
            e = m.embeds[0]
            if not _is_provider_answer_embed(e): return
            await self.client.incrby(self.senior_key, int(self.delta))
            log.info("[qna-award] +%s XP key=%s msg=%s", self.delta, self.senior_key, getattr(m,"id",None))
        except Exception as exc:
            log.warning("[qna-award] failed: %r", exc)

async def setup(bot): await bot.add_cog(QnaAnswerAwardXP(bot))
