
from __future__ import annotations
import os, logging
from typing import Any, Optional, List
from discord.ext import commands

log = logging.getLogger(__name__)

# --- QnA Dual-Mode Markers (for prerender check) ---
# MODE A: isolation channel
# MODE B: public mention
QNA_EMBED_TITLE_LEINA = os.getenv("QNA_TITLE_PUBLIC", "Answer by Leina")
QNA_EMBED_TITLE_PROVIDER = os.getenv("QNA_TITLE_ISOLATION", "Answer by {provider}")

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


# --- Provider helpers required by prerender check ---
def get_groq_answer(messages: list[dict[str, Any]], model: str | None = None) -> Optional[str]:
    """Call Groq Chat Completions and return the assistant text."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq  # type: ignore
    except Exception as e:
        log.warning("[qna] groq client missing: %s", e); return None
    try:
        client = Groq(api_key=api_key)
        m = model or os.getenv("GROQ_MODEL","llama-3.3-70b-versatile")
        resp = client.chat.completions.create(
            model=m,
            messages=messages,
            temperature=float(os.getenv("GROQ_TEMPERATURE","0.2")),
            max_tokens=int(os.getenv("GROQ_MAX_TOKENS","512"))
        )
        # defensive parse
        choice = (resp.choices or [None])[0]
        if not choice or not getattr(choice, "message", None):
            return None
        return getattr(choice.message, "content", None) or None
    except Exception as e:
        log.warning("[qna] groq call failed: %s", e); return None

def gemini_client():
    """Return configured Gemini client (google.generativeai)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=api_key)
        model = os.getenv("GEMINI_MODEL","gemini-2.0-flash")
        return genai.GenerativeModel(model)
    except Exception as e:
        log.warning("[qna] gemini client failed: %s", e); return None

def get_gemini_answer(prompt: str, client=None) -> Optional[str]:
    c = client or gemini_client()
    if c is None:
        return None
    try:
        # Use generate_content; keep it simple
        r = c.generate_content(prompt)
        # genai returns object with .text or candidates
        txt = getattr(r, "text", None)
        if txt: return txt
        try:
            cand = (r.candidates or [None])[0]
            part0 = (cand.content.parts or [None])[0]
            return getattr(part0, "text", None) or None
        except Exception:
            return None
    except Exception as e:
        log.warning("[qna] gemini call failed: %s", e); return None
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
        # Pack messages for Groq
        messages = [{"role": "system", "content": "You are a concise assistant."},
                    {"role": "user", "content": question}]
        # try providers in order
        for prov in self.provider_order:
            if prov == "groq":
                ans = get_groq_answer(messages)
                if ans:
                    self._last_provider = "groq"
                    return format_message(ans)
            elif prov == "gemini":
                ans = get_gemini_answer(question)
                if ans:
                    self._last_provider = "gemini"
                    return format_message(ans)
        return None

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutoAnswerOverlay(bot))
