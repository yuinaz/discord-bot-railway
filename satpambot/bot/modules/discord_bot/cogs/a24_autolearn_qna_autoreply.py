import os, logging, httpx, discord
from discord.ext import commands

log = logging.getLogger(__name__)

class AutoLearnQnAAutoReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.QNA_CHANNEL_ID = getattr(self.bot.get_cog("QnaDualProvider") or self.bot, "QNA_CHANNEL_ID", None) \
            or int(os.getenv("QNA_CHANNEL_ID") or 0) or None

    async def _ask_http_groq(self, prompt: str):
        key = os.getenv("GROQ_API_KEY")
        if not key: return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as x:
                r = await x.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}]}
                )
                r.raise_for_status()
                j = r.json()
                return j["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log.warning("[autolearn] groq fallback failed: %r", e)
            return None

    async def _ask_http_gemini(self, prompt: str):
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key: return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as x:
                r = await x.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents":[{"role":"user","parts":[{"text":prompt}]}]}
                )
                r.raise_for_status()
                j = r.json()
                return j["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            log.warning("[autolearn] gemini fallback failed: %r", e)
            return None

    async def _ask_llm(self, prompt: str) -> str | None:
        ask = getattr(self.bot, "llm_ask", None)
        if ask:
            try:
                res = await ask(prompt)
                if res: return str(res).strip()
            except Exception as e:
                log.warning("[autolearn] llm_ask failed: %r", e)
        return await self._ask_http_groq(prompt) or await self._ask_http_gemini(prompt)

    def _is_qna_channel(self, message: discord.Message) -> bool:
        return (self.QNA_CHANNEL_ID and message.channel.id == self.QNA_CHANNEL_ID) or (self.QNA_CHANNEL_ID is None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        if not self._is_qna_channel(message): return
        q = (message.content or "").strip()
        if not q: return

        ans = await self._ask_llm(q)
        if not ans:
            log.info("[autolearn] no answer")
            return

        emb = discord.Embed(title="QnA AutoLearn", color=0x3b82f6)
        emb.add_field(name="Question (Leina)", value=q[:1024] or "-", inline=False)
        emb.add_field(name="Answer", value=ans[:1024] or "-", inline=False)
        emb.set_footer(text="AutoLearn • dual-provider (Groq/Gemini)")
        await message.channel.send(embed=emb)

async def setup(bot):
    await bot.add_cog(AutoLearnQnAAutoReply(bot))
