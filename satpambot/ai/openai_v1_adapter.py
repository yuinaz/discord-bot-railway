# Unified OpenAI/Groq adapter (OpenAI-compatible API)
# Drop-in pengganti: satpambot/ai/openai_v1_adapter.py
from __future__ import annotations
from typing import List, Dict, Optional
import os, asyncio, logging
from openai import OpenAI
from openai import RateLimitError

log = logging.getLogger(__name__)

def _mk_client():
    provider = (os.getenv("AI_PROVIDER") or "").lower()
    if not provider and os.getenv("GROQ_API_KEY"):
        provider = "groq"  # auto-pick groq kalau ada key-nya

    if provider == "groq":
        api_key  = os.getenv("GROQ_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.groq.com/openai/v1")
        model    = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        name     = "groq"
    else:
        api_key  = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or None
        model    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        name     = "openai"

    if not api_key:
        raise RuntimeError(f"[ai] Missing API key for provider '{name}'")

    cli = OpenAI(api_key=api_key, base_url=base_url)
    return name, model, cli

PROVIDER, DEFAULT_MODEL, CLIENT = _mk_client()

async def achat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    **kwargs,
) -> str:
    """Chat completion (OpenAI or Groq via OpenAI-compatible endpoint)."""
    mdl = model or DEFAULT_MODEL
    loop = asyncio.get_running_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: CLIENT.chat.completions.create(
                model=mdl,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
        )
        return (resp.choices[0].message.content or "").strip()
    except RateLimitError:
        # Auto fallback ke Groq kalau awalnya OpenAI dan GROQ_API_KEY tersedia
        if PROVIDER != "groq" and os.getenv("GROQ_API_KEY"):
            gcli = OpenAI(
                api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1",
            )
            gmodel = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            resp = await loop.run_in_executor(
                None,
                lambda: gcli.chat.completions.create(
                    model=gmodel,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            )
            return (resp.choices[0].message.content or "").strip()
        raise

async def ask(prompt: str, system: Optional[str] = None, **kw) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await achat(msgs, **kw)
