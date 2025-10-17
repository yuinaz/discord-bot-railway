import os, logging, httpx
from discord.ext import commands
log = logging.getLogger(__name__)

class LlmProviderBootstrapQuietOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not getattr(bot, "llm_ask", None):
            async def _ask(prompt: str) -> str | None:
                # coba providers.LLM jika ada
                try:
                    from satpambot.bot.providers import LLM
                    res = await LLM.ask(prompt)
                    if res: return str(res)
                except Exception:
                    pass
                # fallback Groq → Gemini
                try:
                    async with httpx.AsyncClient(timeout=18.0) as x:
                        gk = os.getenv("GROQ_API_KEY")
                        if gk:
                            r = await x.post(
                                "https://api.groq.com/openai/v1/chat/completions",
                                headers={"Authorization": f"Bearer {gk}", "Content-Type":"application/json"},
                                json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":prompt}]}
                            ); r.raise_for_status()
                            j=r.json(); return j["choices"][0]["message"]["content"].strip()
                        sk = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                        if sk:
                            r = await x.post(
                              f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={sk}",
                              headers={"Content-Type":"application/json"},
                              json={"contents":[{"role":"user","parts":[{"text":prompt}]}]}
                            ); r.raise_for_status()
                            j=r.json(); return j["candidates"][0]["content"]["parts"][0]["text"].strip()
                except Exception as e:
                    log.debug("[llm-bootstrap] http fallback failed: %r", e)
                return None
            setattr(bot, "llm_ask", _ask)

async def setup(bot):
    await bot.add_cog(LlmProviderBootstrapQuietOverlay(bot))
