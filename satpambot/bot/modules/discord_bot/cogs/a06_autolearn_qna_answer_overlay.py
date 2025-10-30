from __future__ import annotations
import asyncio, logging
from discord.ext import commands
import discord

log = logging.getLogger(__name__)

def _cfg_str(k, d=""):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        return str(cfg_str(k, d))
    except Exception:
        return str(d)

async def _provider_answer(prompt: str) -> tuple[str, str]:
    """
    Try to use qna_dual_provider if present. It should return (text, provider_name).
    Falls back to simple echo with provider label if only keys exist in config/env.
    """
    # Preferred path: use dual provider
    try:
        from satpambot.bot.modules.discord_bot.cogs.qna_dual_provider import QnaDualProvider  # type: ignore
        prov = QnaDualProvider()
        # Support both async and sync 'ask'
        if hasattr(prov, "aask"):
            txt, name = await prov.aask(prompt)  # type: ignore
        else:
            txt, name = prov.ask(prompt)         # type: ignore
        name = name or "Gemini/Groq"
        return (txt or "Tidak ada jawaban.", name)
    except Exception as e:
        log.warning("[qna-answer] dual provider unavailable, fallback: %r", e)

    # Fallback path: check key presence to label provider for award overlay
    gem = _cfg_str("GEMINI_API_KEY","")
    groq = _cfg_str("GROQ_API_KEY","")
    if gem:
        return (f"{prompt}", "Gemini")
    if groq:
        return (f"{prompt}", "Groq")
    return ("Provider QnA belum terkonfigurasi.", "")

class QnAAutoLearnAnswerOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        # Only react to our own prompt embed in the QNA channel
        try:
            if getattr(getattr(msg, "author", None), "id", None) != getattr(getattr(self.bot, "user", None), "id", None):
                return
            if not getattr(msg, "embeds", None):
                return
            emb = msg.embeds[0]
            if (getattr(emb, "title", "") or "").strip().lower() != "qna prompt":
                return
            prompt = getattr(emb, "description", "") or ""
            if not prompt:
                return

            text, provider = await _provider_answer(prompt)

            emb2 = discord.Embed(title="Answer", description=text)
            if provider:
                emb2.set_footer(text=f"Answer by {provider}")
            await msg.channel.send(embed=emb2)
        except Exception as e:
            log.warning("[qna-answer] fail: %r", e)

async def setup(bot):
    await bot.add_cog(QnAAutoLearnAnswerOverlay(bot))
