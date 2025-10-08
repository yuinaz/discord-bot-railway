# -*- coding: utf-8 -*-
"""
OpenAI v1-like adapter that proxies to Groq so old code paths continue to work.
Only implements what's needed by our bot (chat.completions.create).
"""
from __future__ import annotations
from typing import Any, Dict, Iterable
import types

from .groq_client import make_groq_client, GroqLLM


class _ChoicesObj:
    def __init__(self, content: str, role: str = "assistant"):
        self.message = types.SimpleNamespace(content=content, role=role)
        self.delta = types.SimpleNamespace(content=None)  # for stream compatibility


class _ResponseObj:
    def __init__(self, content: str):
        self.choices = [_ChoicesObj(content)]


class _StreamChunk:
    def __init__(self, delta: str):
        self.choices = [types.SimpleNamespace(delta=types.SimpleNamespace(content=delta))]


class _Completions:
    def __init__(self, llm: GroqLLM):
        self.llm = llm

    def create(self, **kwargs):
        stream = kwargs.get("stream", False)
        messages = kwargs.get("messages", [])
        # map a few common params
        gen = {}
        for k in ("temperature", "max_tokens", "top_p"):
            if k in kwargs:
                gen[k] = kwargs[k]
        if stream:
            def _generator():
                for delta in self.llm.complete_stream(messages, **gen):
                    yield _StreamChunk(delta)
            return _generator()
        else:
            content = self.llm.complete(messages, **gen)
            return _ResponseObj(content)


class _Chat:
    def __init__(self, llm: GroqLLM):
        self.completions = _Completions(llm)


class OpenAIV1Like:
    def __init__(self):
        client = make_groq_client()
        self._llm = GroqLLM(client)

    @property
    def chat(self):
        return _Chat(self._llm)


def get_client() -> OpenAIV1Like:
    """Factory used by hotfixes."""
    return OpenAIV1Like()
