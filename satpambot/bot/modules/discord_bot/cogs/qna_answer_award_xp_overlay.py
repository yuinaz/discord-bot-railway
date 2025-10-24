
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

from .....config.auto_defaults import cfg_int, cfg_str
import logging
log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient = None

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
            title = (getattr(e, "title", "") or "").lower()
            if "answer" not in title: return
            if not await self._mark_once(int(m.id)): return
            if not self.client or not getattr(self.client, "enabled", False): return
            await self.client.incrby(self.senior_key, int(self.delta))
            log.info("[qna-award] +%s XP to BOT (key=%s) msg=%s", self.delta, self.senior_key, m.id)
        except Exception as e:
            log.warning("[qna-award] failed: %r", e)

async def setup(bot): await bot.add_cog(QnaAnswerAwardXP(bot))