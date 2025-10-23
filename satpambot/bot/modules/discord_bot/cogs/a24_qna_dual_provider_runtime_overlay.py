
"""
a24_qna_dual_provider_runtime_overlay.py
- Non-invasive QnA command for Leina.
- Adds /qna (alias: /ask) with provider "groq" or "gemini".
- Respects QNA channel gate via env QNA_CHANNEL_ID (or reuse static id from qna_dual_provider.py if present).
- Uses httpx to call providers directly. No dependency on llm_providers.*
"""

from __future__ import annotations
import os, asyncio, logging, json
from typing import Optional
from discord.ext import commands

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

log = logging.getLogger(__name__)

def _env_pick(k: str) -> Optional[str]:
    v = os.getenv(k)
    if v: return v
    if k == "UPSTASH_REST_URL":
        return os.getenv("UPSTASH_REDIS_REST_URL")
    if k == "UPSTASH_REST_TOKEN":
        return os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if k == "GEMINI_API_KEY":
        return os.getenv("GOOGLE_API_KEY")
    return None

def _qna_channel_id(bot) -> Optional[int]:
    # Prefer env override
    env = os.getenv("QNA_CHANNEL_ID")
    if env:
        try:
            return int(env)
        except:  # pragma: no cover
            pass
    # If legacy stub exists, reuse its constant to avoid mismatch
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.cogs.qna_dual_provider", fromlist=["QNA_CHANNEL_ID"])
        return int(getattr(mod, "QNA_CHANNEL_ID", 0)) or None
    except Exception:
        return None

async def _ask_groq(prompt: str, model: Optional[str] = None) -> str:
    if httpx is None:
        raise RuntimeError("httpx missing")
    key = _env_pick("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    m = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {"model": m, "messages":[{"role":"user","content":prompt}], "temperature": 0.6}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload)
        r.raise_for_status()
        data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return json.dumps(data)[:1200]

async def _ask_gemini(prompt: str, model: Optional[str] = None) -> str:
    if httpx is None:
        raise RuntimeError("httpx missing")
    key = _env_pick("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    m = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    payload = {"contents":[{"parts":[{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return json.dumps(data)[:1200]

class QnaDualProviderOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.qna_channel_id = _qna_channel_id(bot)
        log.info("[qna-overlay] ready; qna_channel_id=%s", self.qna_channel_id)

    @commands.hybrid_command(name="qna", with_app_command=True, description="Tanya LLM (groq/gemini).")
    async def qna(self, ctx: commands.Context, *, prompt: str):
        """Default provider = groq; override via /qna_gemini atau /ask_groq model=.."""
        await self._handle(ctx, prompt, provider=os.getenv("QNA_PROVIDER","groq"))

    @commands.hybrid_command(name="ask", with_app_command=True, description="Alias qna.")
    async def ask(self, ctx: commands.Context, *, prompt: str):
        await self._handle(ctx, prompt, provider=os.getenv("QNA_PROVIDER","groq"))

    @commands.hybrid_command(name="qna_groq", with_app_command=True, description="Tanya via Groq.")
    async def qna_groq(self, ctx: commands.Context, *, prompt: str):
        await self._handle(ctx, prompt, provider="groq")

    @commands.hybrid_command(name="qna_gemini", with_app_command=True, description="Tanya via Gemini.")
    async def qna_gemini(self, ctx: commands.Context, *, prompt: str):
        await self._handle(ctx, prompt, provider="gemini")

    async def _handle(self, ctx: commands.Context, prompt: str, provider: str):
        # Gate: only in QNA channel if defined
        if self.qna_channel_id and getattr(ctx.channel, "id", None) != self.qna_channel_id:
            try:
                await ctx.reply(f"Gunakan thread/tchannel QnA ya (<#{self.qna_channel_id}>).", ephemeral=True)
            except Exception:
                pass
            return
        try:
            if provider.lower().startswith("groq"):
                ans = await _ask_groq(prompt)
            else:
                ans = await _ask_gemini(prompt)
        except Exception as e:
            ans = f"QnA error: {e}"
        try:
            await ctx.reply(ans, mention_author=False)
        except Exception:
            await ctx.send(ans)

async def setup(bot):
    await bot.add_cog(QnaDualProviderOverlay(bot))
