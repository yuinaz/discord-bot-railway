# a06_autolearn_qna_answer_overlay.py
# Robust autolearn → QnA embed answerer (no config changes).
import os, re, logging, datetime, asyncio
from typing import Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

AUTOLEARN_RE = re.compile(r'^\s*\[(?:auto[\-\s]?learn)\]\s*$', re.I | re.M)
QUESTION_RE  = re.compile(r'^\s*Q:\s*(.+)$', re.I | re.M)

def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else d

def _qna_id():
    raw = _env("LEARNING_QNA_CHANNEL_ID") or _env("QNA_CHANNEL_ID")
    try: return int(raw) if raw else None
    except: return None

def _provider_label():
    prov = (_env("LLM_PROVIDER","auto") or "auto").lower()
    groq = _env("LLM_GROQ_MODEL","llama-3.1-8b-instant")
    gem  = _env("LLM_GEMINI_MODEL","gemini-2.5-flash-lite")
    if prov == "groq": name="Groq"; footer=f"groq:{groq}"
    elif prov == "gemini": name="Gemini"; footer=f"gemini:{gem}"
    else: name="LLM"; footer=f"auto(groq={groq},gemini={gem})"
    return name, footer

class AutoLearnQnaAnswerOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.qna_id = _qna_id()
        self._answered = set()

    async def _ask(self, prompt: str) -> str:
        # primary path
        if hasattr(self.bot, "llm_ask"):
            try:
                out = await self.bot.llm_ask(
                    prompt,
                    system="Jawab ringkas, jelas, actionable. Gunakan bullet jika cocok.",
                    temperature=0.2,
                )
                if out and out.strip():
                    return out.strip()
            except Exception as e:
                log.warning("[autolearn] llm_ask failed primary: %r", e)
        # fallback: try providers facade if available
        try:
            from satpambot.bot import llm_providers as providers
            if hasattr(providers, "LLM"):
                out = await providers.LLM.ask(prompt, system="Ringkas dan teknis.", temperature=0.2)
                if out and out.strip():
                    return out.strip()
        except Exception as e:
            log.debug("[autolearn] providers.LLM fallback not available: %r", e)
        return ""

    async def _send_embed(self, ch: discord.TextChannel, q: str, a: str, ref: Optional[discord.MessageReference] = None):
        name, footer = _provider_label()
        emb = discord.Embed(title="QnA", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
        emb.add_field(name="Question by Leina", value=q[:1024] if q else "-", inline=False)
        emb.add_field(name=f"Answer by {name}", value=a[:1024] if a else "—", inline=False)
        emb.set_footer(text=footer)
        await ch.send(embed=emb, reference=ref) if ref else await ch.send(embed=emb)

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        # hanya di channel QNA jika disetel
        if self.qna_id and m.channel.id != self.qna_id:
            return
        if not m.content or m.author.bot is False:
            # auto-learn post biasanya dari bot; tetapi jika kamu ingin user, hapus kondisi ini
            pass
        if not AUTOLEARN_RE.search(m.content):
            return
        mm = QUESTION_RE.search(m.content)
        if not mm:
            return
        if m.id in self._answered:
            return
        q = mm.group(1).strip()
        ans = await self._ask(q)
        if not ans:
            log.info("[autolearn] no answer")
            return
        try:
            await self._send_embed(m.channel, q, ans, m.to_reference())
            self._answered.add(m.id)
        except Exception as e:
            log.warning("[autolearn] embed send failed: %r", e)

async def setup(bot):
    await bot.add_cog(AutoLearnQnaAnswerOverlay(bot))
