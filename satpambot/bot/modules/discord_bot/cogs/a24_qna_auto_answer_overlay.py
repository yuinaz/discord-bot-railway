
from __future__ import annotations
import os, logging
from typing import Any, Optional, List
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_bool(key: str, default: bool=False) -> bool:
    v = os.getenv(key)
    if v is None: return default
    return str(v).strip().lower() in {"1","true","yes","on"}

def _get_groq_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def _get_groq_fallbacks() -> List[str]:
    raw = os.getenv("GROQ_MODEL_FALLBACKS", "llama-3.1-8b-instant")
    return [m.strip() for m in raw.split(",") if m.strip()]

def _groq_chat(messages: list[dict[str, Any]]) -> Optional[str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq  # type: ignore
    except Exception as e:
        log.warning("[qna] groq helper not found: %s", e)
        return None
    client = Groq(api_key=api_key)
    try_order = [_get_groq_model()] + _get_groq_fallbacks()
    last_err = None
    for m in try_order:
        try:
            resp = client.chat.completions.create(model=m, messages=messages, temperature=0.6)
            return resp.choices[0].message.content
        except Exception as e:  # 4xx/5xx or network
            last_err = e
            continue
    log.warning("[qna] groq failed: %s", last_err)
    return None

def _gemini_chat(prompt: str) -> Optional[str]:
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)
        return getattr(resp, "text", None) or None
    except Exception as e:
        log.warning("[qna] gemini failed: %s", e)
        return None

class QnaAutoAnswerOverlay(commands.Cog):
    """
    Lightweight, import-safe overlay. Actual QnA driving can be handled by neuro_autolearn module.
    This overlay only exposes safe helpers; no background loops at import-time.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.provider_order = [s.strip() for s in os.getenv("QNA_PROVIDER", os.getenv("QNA_PROVIDER_ORDER", "groq,gemini")).split(",") if s.strip()]
        log.info("[qna] providers=%s", self.provider_order)

    def answer(self, question: str) -> Optional[str]:
        # Pack messages for Groq style
        messages = [{"role": "system", "content": "You are a concise assistant."},
                    {"role": "user", "content": question}]
        for prov in self.provider_order:
            if prov == "groq":
                ans = _groq_chat(messages)
                if ans: return ans
            elif prov == "gemini":
                ans = _gemini_chat(question)
                if ans: return ans
        return None

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutoAnswerOverlay(bot))
