
from discord.ext import commands
def _get_conf():
    try:
        from satpambot.config.compat_conf import get_conf
        return get_conf
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf
            return get_conf
        except Exception:
            def _f(): return {}
            return _f

import re, discord

from satpambot.ml.neuro_lite_rewards import award_points_all

KEYWORDS = ("phish", "phishing", "phash", "ban", "enforce")

class PhishRewardListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _get_conf()()

    def _is_log_channel(self, ch_id: int) -> bool:
        target = int(str(self.cfg.get("PHISH_LOG_CHANNEL_ID", self.cfg.get("LOG_CHANNEL_ID","0"))) or 0)
        return target and (ch_id == target)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only own messages in log channel/thread
        if not message or message.author.id != self.bot.user.id:
            return
        ch = message.channel
        base_id = getattr(getattr(ch, "parent", None), "id", None) or getattr(ch, "id", 0)
        if not self._is_log_channel(int(base_id)):
            return

        # Detect enforcement log via embed/title/content keywords
        text = (message.content or "").lower()
        titles = [ (e.title or "").lower() for e in message.embeds ]
        joined = " ".join([text] + titles)
        if any(k in joined for k in KEYWORDS):
            # Reward once per message (simple heuristic)
            await award_points_all(self.bot, n=1, reason="phish-ban")
async def setup(bot: commands.Bot):
    await bot.add_cog(PhishRewardListener(bot))