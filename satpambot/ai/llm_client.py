# -*- coding: utf-8 -*-
"""
Unified LLM entrypoint for SatpamBot (Groq-only).
Usage:
    from satpambot.ai.llm_client import make_client
    client = make_client()
    text = client.complete(messages)
"""
from __future__ import annotations

from .groq_client import make_groq_client, GroqLLM


def make_client():
    """
    Create a default GroqLLM bound to GROQ_* env vars.
    Raises RuntimeError when key not set to avoid noisy channel messages.
    """
    cli = make_groq_client()
    return GroqLLM(cli)
