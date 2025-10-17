import os, logging
from discord.ext import commands
import discord

log = logging.getLogger(__name__)

QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID","0") or "0")

class AutolearnQnAAutoReplyFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not QNA_CHANNEL_ID or msg.guild is None: return
        if msg.channel.id != QNA_CHANNEL_ID: return
        if msg.author.bot: return
        content = (msg.content or "").strip()
        if not content: return

        # Call provider via unified hook
        ans = None; provider = "unknown"
        try:
            if hasattr(self.bot, "llm_ask"):
                ans = await self.bot.llm_ask(content, prefer=os.getenv("LLM_PREFER","groq"))
                provider = os.getenv("LLM_PREFER","groq").upper()
        except Exception as e:
            log.warning("[autolearn-qna] provider error: %s", e)
        if not ans:
            ans = "(no answer from provider)"

        emb = discord.Embed(title="Auto QnA", colour=discord.Colour.blurple())
        emb.add_field(name="Question (Leina)", value=content[:1024] or "-", inline=False)
        emb.add_field(name=f"Answer ({provider})", value=ans[:1024], inline=False)
        emb.set_footer(text="autolearn • Q&A")

        try:
            await msg.channel.send(embed=emb)
        except Exception as e:
            log.warning("[autolearn-qna] send embed failed: %s", e)

async def setup(bot):
    await bot.add_cog(AutolearnQnAAutoReplyFix(bot))
