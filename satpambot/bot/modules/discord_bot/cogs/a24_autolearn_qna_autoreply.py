
# a24_autolearn_qna_autoreply.py (v7.4 — embed)
import os, re, logging, datetime, discord
from discord.ext import commands
log = logging.getLogger(__name__)
def _env(k, d=None):
    v = os.getenv(k, d)
    if isinstance(v, str): return v.strip()
    return v
def _provider_model_label():
    p = (_env("LLM_PROVIDER","auto") or "auto").lower()
    if p == "groq": m=_env("LLM_GROQ_MODEL","llama-3.1-70b-versatile")
    elif p == "gemini": m=_env("LLM_GEMINI_MODEL","gemini-1.5-flash")
    elif p == "cli": m=_env("LLM_CLI_MODEL","gpt-4o-mini")
    else: m=_env("LLM_GROQ_MODEL") or _env("LLM_GEMINI_MODEL") or _env("LLM_CLI_MODEL") or "auto"
    return f"{p}:{m}"
class AutoLearnQnAAutoreply(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _send_embed(self, where, question, answer, reference=None):
        title = _env("AUTOLEARN_EMBED_TITLE","Auto-learn Answer")
        color_hex = _env("AUTOLEARN_EMBED_COLOR","0x00B2FF")
        try: color=int(color_hex,16) if isinstance(color_hex,str) else int(color_hex)
        except Exception: color=0x00B2FF
        e=discord.Embed(title=title, color=color, timestamp=datetime.datetime.utcnow())
        e.add_field(name="Pertanyaan", value=(question or "-")[:1024], inline=False)
        e.add_field(name="Jawaban", value=(answer or "-")[:1024], inline=False)
        e.set_footer(text=_env("AUTOLEARN_EMBED_FOOTER", _provider_model_label()))
        await where.send(embed=e, reference=reference) if reference else await where.send(embed=e)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not self.bot.user or message.author.id != self.bot.user.id: return
            text=(message.content or "").strip()
            if not text.startswith("[auto-learn]"): return
            m=re.search(r"^Q:\s*(.+)$", text, re.MULTILINE)
            if not m: return
            q=m.group(1).strip()
            ask=getattr(self.bot,"llm_ask",None)
            if not ask: log.info("[autolearn] llm provider not ready"); return
            ans=await ask(q, system="Jawab ringkas, fokus langkah praktis. Bahasa Indonesia.", temperature=0.2)
            if not ans: log.info("[autolearn] no LLM answer"); return
            use_embed = _env("AUTOLEARN_EMBED","1")=="1"
            target = (message.thread if (message.thread and not getattr(message.thread,'archived',False)) else message.channel)
            ref = (None if target is message.thread else message)
            if use_embed: await self._send_embed(target, q, ans, reference=ref)
            else: await target.send(f"[auto-learn:answer]\n**Q:** {q}\n**A:** {ans}", reference=ref)
        except Exception as e:
            log.info("[autolearn] on_message failed: %r", e)
async def setup(bot):
    try: await bot.add_cog(AutoLearnQnAAutoreply(bot))
    except Exception as e: log.info("[autolearn] setup swallowed: %r", e)
