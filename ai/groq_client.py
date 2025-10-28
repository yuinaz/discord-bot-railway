"""Legacy shim — canonical implementation moved to `satpambot.ai.groq_client`.

This module exists for backward compatibility. Importing from `ai.groq_client`
will re-export the symbols from `satpambot.ai.groq_client` but will emit a
DeprecationWarning so callers switch to the new package path.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.groq_client' is deprecated; use 'satpambot.ai.groq_client' instead", DeprecationWarning)
from satpambot.ai.groq_client import *  # type: ignore

def _log_call(messages: List[Dict]):
    if not LOG_LLM_CALLS:
        return
    # Coba identifikasi modul/fungsi pemanggil di dalam package
    mod = func = "?"
    try:
        for frame in inspect.stack()[1:]:
            fname = (frame.filename or "").replace("\\\\","/")
            if "/satpambot/" in fname and not fname.endswith("/ai/groq_client.py"):
                mod = fname.split("/satpambot/")[-1]
                func = frame.function
                break
        content_len = sum(len(m.get("content","") or "") for m in messages if m.get("role") in ("user","system"))
    except Exception:
        content_len = 0
    print(f"[LLM] caller={mod}:{func} content_len={content_len} model={MODEL}", flush=True)

class GroqLLM:
    def __init__(self, client: "Groq", model: Optional[str] = None, max_tokens: int = 256, timeout_s: int = 60):
        if client is None:
            raise RuntimeError("Groq client unavailable; install groq SDK or set secret GROQ_API_KEY.")
        self.client = client
        self.model = model or MODEL
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def complete(self, messages: List[Dict]) -> str:
        _maybe_wait()
        _log_call(messages)
        p = {"max_tokens": self.max_tokens}
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, **p
        )
        return resp.choices[0].message.content

    def stream(self, messages: List[Dict]):
        _maybe_wait()
        _log_call(messages)
        p = {"max_tokens": self.max_tokens}
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **p
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content

def make_groq_client() -> "Groq":
    """Buat client Groq. API key diambil dari secrets/local (get_secret)."""
    if Groq is None:
        raise RuntimeError("Package 'groq' tidak tersedia. `pip install groq`.")
    api_key = (get_secret("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY tidak ditemukan di secrets/local. "
                           "Taruh di: secrets/groq_api_key.txt atau di satpambot_config.local.json.secrets")
    return Groq(api_key=api_key)
