import inspect, logging, discord
from discord.ext import commands

logger = logging.getLogger(__name__)
MAX_FIELD = 1024

def _persona_name(bot) -> str:
    po = bot.get_cog("PersonaOverlay")
    fn = getattr(po, "get_active_persona", None) if po else None
    if callable(fn):
        try:
            return fn() if not inspect.iscoroutinefunction(fn) else "leina"
        except Exception:
            pass
    for attr in ("active", "ACTIVE", "DEFAULT", "default_name"):
        v = getattr(po, attr, None) if po else None
        if isinstance(v, str) and v:
            return v
    return "leina"

async def _llm_call(bot, prompt: str, system: str):
    for provider in ("groq", "gemini"):
        try:
            fn = getattr(bot, "llm_ask", None)
            if not callable(fn):
                raise RuntimeError("bot.llm_ask missing")
            try:
                return await fn(prompt, system=system, provider=provider), provider
            except TypeError:
                return await fn(prompt, provider=provider), provider
        except Exception as e:
            logger.warning("[autolearn-fix] %s failed: %r", provider, e)
            continue
    return "", ""

class AutoLearnQnAAutoReplyFixOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot:
            return
        ch_id = getattr(self.bot, "QNA_CHANNEL_ID", None)
        if not ch_id or m.channel.id != ch_id:
            return

        q = (m.content or "").strip()
        if not q:
            return

        persona = _persona_name(self.bot)
        system = f"Kamu adalah {persona}. Jawab singkat, jelas, dan ramah."

        ans, src = await _llm_call(self.bot, q, system)
        if not ans:
            return

        e = discord.Embed(title="[auto-learn]", color=0x3b82f6)
        e.add_field(name="Q", value=(q[:MAX_FIELD] or "-"), inline=False)
        e.add_field(name=f"A · {src}", value=(ans[:MAX_FIELD] or "-"), inline=False)
        e.set_footer(text=f"#{persona} • auto")
        await m.channel.send(embed=e)

async def setup(bot):
    await bot.add_cog(AutoLearnQnAAutoReplyFixOverlay(bot))
