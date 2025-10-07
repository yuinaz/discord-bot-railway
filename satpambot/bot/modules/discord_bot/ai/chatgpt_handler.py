from __future__ import annotations
import logging
from typing import Optional
from satpambot.ai.openai_v1_adapter import chat_completion_create

async def call_chatgpt(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    """Non-stream simple wrapper using OpenAI SDK v1 adapter.
    - Relies on OPENAI_API_KEY via adapter (env/secret handled there).
    - Safe to import; network only on call.
    """
    try:
        resp = chat_completion_create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        # Adapter returns the SDK response object (synchronous); allow both sync/async call sites.
        # If the adapter is used in an async context somewhere else, that wrapper should await itself.
        content: Optional[str] = None
        try:
            # OpenAI 1.x/2.x style
            content = resp.choices[0].message.content  # type: ignore[attr-defined]
        except Exception:
            # Fallback for unexpected structures
            content = str(resp)
        return (content or "").strip()
    except Exception as e:
        logging.error("❌ Gagal memanggil ChatGPT (v1 adapter): %s", e, exc_info=True)
        return "❌ Terjadi kesalahan saat memanggil ChatGPT."
