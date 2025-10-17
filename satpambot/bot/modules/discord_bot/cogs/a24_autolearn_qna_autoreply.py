# -*- coding: utf-8 -*-
import os, asyncio, logging, datetime, json
from typing import Optional
import discord
from discord.ext import commands

LOG = logging.getLogger(__name__)

def _env(name: str, default: Optional[str]=None) -> Optional[str]:
    v = os.environ.get(name)
    return v if v not in (None, "") else default

def _provider_name() -> str:
    p = (_env("LLM_PROVIDER","auto") or "auto").lower()
    if p == "groq": return "Groq"
    if p == "gemini": return "Gemini"
    if p == "cli": return "CLI"
    return "LLM"

def _provider_model_label() -> str:
    groq = _env("LLM_GROQ_MODEL","llama-3.1-8b-instant")
    gem  = _env("LLM_GEMINI_MODEL","gemini-2.5-flash-lite")
    p = (_env("LLM_PROVIDER","auto") or "auto").lower()
    if p == "groq": return f"groq:{groq}"
    if p == "gemini": return f"gemini:{gem}"
    return f"auto(groq={groq},gemini={gem})"

def _qna_channel_id() -> Optional[int]:
    v = _env("LEARNING_QNA_CHANNEL_ID") or _env("QNA_CHANNEL_ID")
    try: return int(v) if v else None
    except: return None

class AutoLearnQnAAutoreply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.qna_channel_id = _qna_channel_id()

    async def _send_embed(self, where: discord.TextChannel, question: str, answer: str, reference=None):
        color = discord.Color.blue()
        e = discord.Embed(title=_env("AUTOLEARN_EMBED_TITLE","QnA"),
                          color=color, timestamp=datetime.datetime.utcnow())
        e.add_field(name="Question by Leina", value=(question or "-")[:1024], inline=False)
        e.add_field(name=f"Answer by {_provider_name()}", value=(answer or "-")[:1024], inline=False)
        e.set_footer(text=_env("AUTOLEARN_EMBED_FOOTER", _provider_model_label()))
        await where.send(embed=e, reference=reference) if reference else await where.send(embed=e)

    async def _answer_with_llm(self, text: str) -> str:
        fn = getattr(self.bot, "llm_ask", None)
        if not fn:
            return "LLM is not available."
        prompt = f"Answer briefly and clearly:\n\n{text}"
        out = await fn(prompt, system="Be concise and accurate.", temperature=0.3)
        return out or "No answer."

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        ch_id = self.qna_channel_id
        if not ch_id:
            return
        if message.channel.id != ch_id:
            return
        # Only answer messages that mention the bot or start with '?'
        if not (self.bot.user in message.mentions or message.content.strip().startswith("?")):
            return
        q = message.content.strip().lstrip("?").strip()
        ans = await self._answer_with_llm(q)
        await self._send_embed(message.channel, q, ans, reference=message.to_reference())

async def setup(bot):
    await bot.add_cog(AutoLearnQnAAutoreply(bot))
