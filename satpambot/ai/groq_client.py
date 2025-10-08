# -*- coding: utf-8 -*-
"""
Groq-only client helper for SatpamBot.
- Fail-fast when GROQ_API_KEY is missing to avoid noisy error embeds.
- Simple non-stream and stream APIs.
"""
from __future__ import annotations
import os
from typing import Iterable, List, Dict, Optional

# Import lazily to keep smoketests offline-friendly.
try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None  # allow import in environments without groq installed


def _get_api_key() -> str:
    for k in ("GROQ_API_KEY", "GROQ_KEY", "GROQ_TOKEN"):
        v = os.getenv(k)
        if v:
            return v
    raise RuntimeError("GROQ_API_KEY not set. Set env GROQ_API_KEY (or GROQ_KEY/GROQ_TOKEN).")


DEFAULT_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
BASE_URL = os.getenv("GROQ_BASE_URL") or None


def make_groq_client(api_key: Optional[str] = None):
    """
    Returns a Groq SDK client. Raises RuntimeError if no key.
    """
    api_key = api_key or _get_api_key()
    if Groq is None:
        raise RuntimeError("groq package not installed. pip install groq")
    kwargs = {"api_key": api_key}
    if BASE_URL:
        kwargs["base_url"] = BASE_URL
    return Groq(**kwargs)


class GroqLLM:
    def __init__(self, client, model: Optional[str] = None, **gen_defaults):
        self.client = client
        self.model = model or DEFAULT_MODEL
        self.defaults = {"temperature": float(os.getenv("GROQ_TEMP", "0.2")),
                         "max_tokens": int(float(os.getenv("GROQ_MAX_TOKENS", "512")))}
        self.defaults.update(gen_defaults)

    def complete(self, messages: List[Dict[str, str]], **opts) -> str:
        p = self.defaults.copy()
        p.update(opts)
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=False, **p
        )
        return (resp.choices[0].message.content or "") if resp and resp.choices else ""

    def complete_stream(self, messages: List[Dict[str, str]], **opts) -> Iterable[str]:
        p = self.defaults.copy()
        p.update(opts)
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **p
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and getattr(delta, "content", None):
                    yield delta.content
            except Exception:
                # be tolerant to SDK variations
                content = getattr(chunk, "content", None)
                if content:
                    yield str(content)
