
import os, asyncio, logging, json, time, re
from collections import deque
from typing import Optional

import discord
from discord.ext import commands

try:
    from ....providers.llm_facade import ask as llm_ask
except Exception as e:
    llm_ask = None
    logging.getLogger(__name__).warning("[autolearn] llm_facade import failed: %r", e)

log = logging.getLogger(__name__)

QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID") or 0) or 1426571542627614772
DEFAULT_PROVIDER = os.getenv("QNA_PROVIDER") or "groq"
DEFAULT_MODEL = os.getenv("QNA_MODEL") or "llama-3.1-8b-instant"

_recent_q_hash = deque(maxlen=64)

def _hash_text(s: str) -> int:
    return hash(re.sub(r"\s+", " ", s.strip().lower()))

def _get_persona_name(bot: commands.Bot) -> str:
    name = None
    for attr in ("get_active_persona", "active_persona", "persona_name"):
        try:
            v = getattr(bot, attr, None)
            name = v() if callable(v) else v
            if name:
                break
        except Exception:
            pass
    return name or "Leina"

class AutoLearnQnAAnswer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot is False:
                return
            if message.channel.id != QNA_CHANNEL_ID:
                return

            content = (message.content or "")
            qtext = None
            if content.strip().startswith("Q:"):
                qtext = content.strip()[2:].strip()
            elif message.embeds:
                emb = message.embeds[0]
                title = (emb.title or "").lower()
                if "question by" in title:
                    qtext = (emb.description or "").strip() or (emb.fields[0].value if emb.fields else "")
                else:
                    desc = (emb.description or "").strip()
                    if desc.lower().startswith("q:"):
                        qtext = desc[2:].strip()

            if not qtext:
                return

            h = _hash_text(qtext)
            if h in _recent_q_hash:
                log.info("[autolearn] skip duplicate question")
                return
            _recent_q_hash.append(h)

            persona = _get_persona_name(self.bot)
            system_prompt = f"You are {persona}, a concise helpful assistant for Discord QnA. Answer briefly but helpfully."

            provider = DEFAULT_PROVIDER
            model = DEFAULT_MODEL
            if "gemini" in (os.getenv("QNA_MODEL") or "").lower():
                provider = "gemini"

            if not llm_ask:
                log.warning("[autolearn] no llm_ask; cannot answer")
                return

            answer = await llm_ask(provider=provider, model=model, system=system_prompt,
                                   messages=[{"role":"user","content": qtext}], temperature=0.6, max_tokens=512)

            e = discord.Embed(title=f"Answer by {provider.title()}", description=answer)
            e.set_footer(text=f"Q: {qtext}")
            try:
                await message.channel.send(embed=e)
            except TypeError:
                await message.channel.send(content=f"**Answer by {provider.title()}**\n{answer}\n\n_Q:_ {qtext}")
        except Exception as e:
            log.warning("[autolearn] error: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLearnQnAAnswer(bot))
