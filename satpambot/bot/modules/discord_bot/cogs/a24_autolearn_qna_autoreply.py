
import os, asyncio, logging, random
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)
QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID") or 0) or 1426571542627614772

SAMPLE_QUESTIONS = [
    "Apa fungsi XP senior di server ini?",
    "Bagaimana cara mendapat XP lebih cepat?",
    "Kenapa bot kadang diam?",
    "Apa itu pHash di anti-phishing?",
]

def _enabled():
    return (os.getenv("QNA_AUTOASK_ENABLED") or "1") not in ("0","false","False")

class AutoAskQnA(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.loop.start()

    def cog_unload(self):
        self.loop.cancel()

    @tasks.loop(minutes=7.5)
    async def loop(self):
        if not _enabled():
            return
        try:
            ch = self.bot.get_channel(QNA_CHANNEL_ID)
            if not ch:
                log.warning("[qna-autoask] QNA channel not found: %s", QNA_CHANNEL_ID)
                return
            q = random.choice(SAMPLE_QUESTIONS)
            emb = discord.Embed(title="Question by Leina", description=q)
            await ch.send(embed=emb)
        except Exception as e:
            log.warning("[qna-autoask] %r", e)

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoAskQnA(bot))
