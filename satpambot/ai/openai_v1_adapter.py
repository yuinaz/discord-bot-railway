from __future__ import annotations
import os
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore
_client = None
def _get_client():
    global _client
    if _client is None:
        if OpenAI is None:
            raise RuntimeError("openai SDK 1.x not installed. Install with: pip install 'openai>=1,<2'")
        _client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    return _client
def chat_completion_create(*, model: str, messages, **kwargs):
    client = _get_client()
    stream = bool(kwargs.pop('stream', False))
    if stream:
        return client.chat.completions.create(model=model, messages=messages, stream=True, **kwargs)
    return client.chat.completions.create(model=model, messages=messages, **kwargs)
