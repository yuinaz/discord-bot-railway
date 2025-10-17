import asyncio, logging, inspect
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

def _persona_name(bot) -> str:
    po = bot.get_cog("PersonaOverlay")
    if po:
        fn = getattr(po, "get_active_persona", None)
        if callable(fn):
            try:
                if inspect.iscoroutinefunction(fn):
                    # Avoid awaiting in getter; fallback to default.
                    return "leina"
                return fn()
            except Exception:
                pass
        # common attributes fallback
        for attr in ("active", "ACTIVE", "DEFAULT", "default_name"):
            v = getattr(po, attr, None)
            if isinstance(v, str) and v:
                return v
    return "leina"

async def _llm_call(bot, prompt: str, system: str):
    # prefer Groq, fallback Gemini; be tolerant with kw args
    for provider in ("groq", "gemini"):
        try:
            fn = getattr(bot, "llm_ask", None)
            if not callable(fn):
                raise RuntimeError("bot.llm_ask missing")
            try:
                return await fn(prompt, system=system, provider=provider), provider
            except TypeError:
                # some facades don't accept 'system' kw
                return await fn(prompt, provider=provider), provider
        except Exception as e:
            logger.warning("[autolearn-answer] %s failed: %r", provider, e)
            continue
    return "", ""

class AutoLearnQnaAnswer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def try_answer(self, channel: discord.TextChannel, msg: discord.Message):
        # Extract question text from embed or content
        q = None
        if msg.embeds:
            e = msg.embeds[0]
            if isinstance(e, discord.Embed):
                q = e.description
        if not q:
            q = (msg.content or "").strip()
        if not q:
            return

        persona = _persona_name(self.bot)
        system = f"Kamu adalah {persona}. Jawab singkat, jelas, ramah, dan to the point."

        ans, src = await _llm_call(self.bot, q, system)
        if not ans:
            return

        e = discord.Embed(title="Answer", description=ans[:4096], color=0x22c55e)
        e.set_footer(text=f"{persona} · {src}")
        await channel.send(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLearnQnaAnswer(bot))
