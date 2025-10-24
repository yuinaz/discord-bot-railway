try:
    import discord
    from discord.ext import commands
except Exception:  # allow smoke import even without discord installed
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

_ANSWER_PATTERNS = [
    r"\banswer\b", r"\bjawaban\b", r"^answer\s*by\b", r"^jawaban\s*oleh\b",
    r"\banswer from\b", r"\bresponse\b"
]
_QUESTION_PATTERNS = [r"\bquestion\b", r"\bpertanyaan\b"]

def _looks_like_answer_embed(e: "discord.Embed") -> bool:
    def safe_lower(x):
        return (x or "").strip().lower()
    title = safe_lower(getattr(e, "title", ""))
    author = safe_lower(getattr(getattr(e, "author", None), "name", None))
    desc = safe_lower(getattr(e, "description", ""))

    # Heuristic: skip clear "Question" embeds
    if any(re.search(p, title) for p in _QUESTION_PATTERNS) and not any(re.search(p, title) for p in _ANSWER_PATTERNS):
        return False
    if any(re.search(p, author) for p in _QUESTION_PATTERNS) and not any(re.search(p, author) for p in _ANSWER_PATTERNS):
        return False

    hay = " ".join([title, author, desc])
    return any(re.search(p, hay) for p in _ANSWER_PATTERNS)

class QnaAnswerAwardXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna_id = cfg_int("QNA_CHANNEL_ID", 0) or None
        self.client = UpstashClient() if UpstashClient else None
        self.delta = int(cfg_str("QNA_XP_PER_ANSWER_BOT", "5") or "5")
        self.senior_key = cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total_v2")
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
            if not _looks_like_answer_embed(e): return
            if not await self._mark_once(int(m.id)): return
            if not self.client or not getattr(self.client, "enabled", False): return
            await self.client.incrby(self.senior_key, int(self.delta))
            log.info("[qna-award] +%s XP to BOT (key=%s) msg=%s", self.delta, self.senior_key, m.id)
        except Exception as exc:
            log.warning("[qna-award] failed: %r", exc)

async def setup(bot): await bot.add_cog(QnaAnswerAwardXP(bot))
