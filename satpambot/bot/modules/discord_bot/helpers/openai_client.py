# -*- coding: utf-8 -*-
"""
Thin wrapper for OpenAI Python SDK v1.
Reads API key from OPENAI_API_KEY or OPENAI-KEY.

Usage:
    from .openai_client import chat_once, chat_stream
"""
import os
from typing import Iterable, List, Dict, Any, Optional

try:
    from openai import OpenAI
except Exception as e:  # pragma: no cover
    OpenAI = None  # type: ignore

def _get_key() -> Optional[str]:
    return os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI-KEY")

def make_client() -> "OpenAI":
    if OpenAI is None:
        raise RuntimeError("OpenAI SDK is not installed. Install `openai>=1,<2`.")
    key = _get_key()
    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY/OPENAI-KEY in env.")
    return OpenAI(api_key=key)

def chat_once(messages: List[Dict[str, str]], model: str = "gpt-4o-mini", **kw) -> str:
    """
    messages: list of dicts like {"role": "user"|"system"|"assistant", "content": "..."}
    returns string content
    """
    client = make_client()
    resp = client.chat.completions.create(model=model, messages=messages, **kw)
    choice = resp.choices[0]
    return getattr(choice.message, "content", "") or ""

def chat_stream(messages: List[Dict[str, str]], model: str = "gpt-4o-mini", **kw) -> Iterable[str]:
    """
    Yields content deltas as strings.
    """
    client = make_client()
    stream = client.chat.completions.create(model=model, messages=messages, stream=True, **kw)
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and getattr(delta, "content", None):
            yield delta.content
