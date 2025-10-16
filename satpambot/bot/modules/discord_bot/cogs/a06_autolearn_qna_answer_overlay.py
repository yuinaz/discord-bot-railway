
"""
a06_autolearn_qna_answer_overlay.py
- Detect messages the bot posts with "[auto-learn]" + "Q:"
- Generate an answer using ProvidersOverlay (LLM) + PersonaOverlay prompt
- Post the answer as an embed reply (and cache via QnAResponseCache if available)
- Cooldown & loop-safe
"""
import asyncio, logging, re, os
from discord.ext import commands
import discord

log = logging.getLogger(__name__)
QUESTION_RE = re.compile(r"\[auto-learn\].*?Q:\s*(.+)", re.I | re.S)
COOLDOWN_SEC = int(os.getenv("AUTOLEARN_COOLDOWN_SEC", "20"))
MAX_LEN = int(os.getenv("AUTOLEARN_MAX_Q_LEN", "600"))

class AutoLearnQnA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_ts = 0

    def _extract_question(self, content: str):
        m = QUESTION_RE.search(content or "")
        if not m:
            return None
        q = (m.group(1) or "").strip()
        return q[:MAX_LEN]

    def _should_skip(self):  # basic global cooldown
        import time
        now = time.time()
        if (now - self._last_ts) < COOLDOWN_SEC:
            return True
        self._last_ts = now
        return False

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        try:
            if message.author.id != getattr(self.bot.user, "id", None):
                return  # only react to our own [auto-learn] prompts
            if "[auto-learn:answer]" in (message.content or ""):
                return
            q = self._extract_question(message.content or "")
            if not q:
                return
            if self._should_skip():
                return

            # Providers + Persona
            prov = self.bot.get_cog("ProvidersOverlay")
            persona = self.bot.get_cog("PersonaOverlay")
            cache = self.bot.get_cog("QnAResponseCache")

            sys_prompt = ""
            if persona:
                data = persona.get_active_persona() or {}
                sys_prompt = (data.get("prompt_prefix") or "")

            # Cache try
            answer = None
            if cache:
                try:
                    answer = await cache.try_get_cached(q)
                except Exception:
                    pass

            if not answer and prov and getattr(prov, "llm", None):
                try:
                    answer = await prov.llm.generate(system_prompt=sys_prompt, messages=[{"role":"user","content":q}], temperature=0.6, max_tokens=512)
                except Exception as e:
                    log.warning("[autolearn] llm failed: %r", e)

            if not answer:
                answer = "Maaf, aku belum yakin. Aku akan belajar dari pertanyaan ini dan coba lagi nanti."

            # Cache set
            if cache:
                try:
                    await cache.cache_answer(q, answer)
                except Exception:
                    pass

            # Send nicely as embed (reply)
            emb = discord.Embed(title="Auto‑learn Answer", description=answer)
            emb.set_footer(text="[auto-learn:answer]")
            try:
                await message.channel.send(embed=emb, reference=message, mention_author=False)
            except TypeError:
                # older discord.py
                await message.channel.send(embed=emb)
        except Exception as e:
            log.warning("[autolearn] error: %r", e)

async def setup(bot):
    await bot.add_cog(AutoLearnQnA(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(AutoLearnQnA(bot)))
    except Exception:
        pass
    return bot.add_cog(AutoLearnQnA(bot))
