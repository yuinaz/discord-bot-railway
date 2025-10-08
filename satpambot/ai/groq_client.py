# -*- coding: utf-8 -*-
"""
Groq-only client helper for SatpamBot (patched: no more persisting gpt-5-mini).
"""
from __future__ import annotations
import os
from typing import Iterable, List, Dict, Optional

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None  # allow import when groq not installed (smoke-safe)

# Lightweight local defaulting without writing to config
def _getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "", "None", "null") else default

def _pick_model() -> str:
    # Priority: GROQ_MODEL > AI_DEFAULT_MODEL (from 20_ai_provider_groq.json if loaded to env) > sane default
    m = _getenv("GROQ_MODEL")
    if m: return m
    m = _getenv("AI_DEFAULT_MODEL")
    if m: return m
    return "llama-3.1-8b-instant"

class GroqLLM:
    def __init__(self, client: "Groq", model: Optional[str] = None, max_tokens: int = 256, timeout_s: int = 60):
        if client is None:
            raise RuntimeError("Groq client unavailable; install groq SDK or set GROQ_API_KEY.")
        self.client = client
        self.model = model or _pick_model()
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def complete(self, messages: List[Dict]) -> str:
        p = {"max_tokens": self.max_tokens}
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, **p
        )
        return resp.choices[0].message.content

    def stream(self, messages: List[Dict]):
        p = {"max_tokens": self.max_tokens}
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **p
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content

def make_groq_client() -> "Groq":
    api_key = _getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set.")
    # Groq SDK: no base_url override needed
    return Groq(api_key=api_key)
