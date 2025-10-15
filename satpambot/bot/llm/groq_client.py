
from __future__ import annotations
import os, asyncio, logging, typing as t
from groq import AsyncGroq
try:
    from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type
except Exception:
    # Fallback shims if tenacity is not installed; retry becomes no-op
    def retry(*a, **kw):
        def deco(fn): return fn
        return deco
    def wait_exponential_jitter(**kw):
        class _Noop: pass
        return _Noop()
    def stop_after_attempt(n):
        class _Noop: pass
        return _Noop()
    def retry_if_exception_type(*e):
        class _Noop: pass
        return _Noop()

log = logging.getLogger(__name__)
_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "25"))
_MAX_CONC = int(os.getenv("LLM_MAX_CONCURRENCY", "3"))
_sem = asyncio.Semaphore(max(1, _MAX_CONC))

def _mk_client() -> AsyncGroq:
    return AsyncGroq()  # reads GROQ_API_KEY

class TransientError(Exception): ...

def _is_transient(e: BaseException) -> bool:
    msg = str(e)
    return any(s in msg for s in (" 429", " 500", " 502", " 503", "Timeout", "ReadTimeout"))

@retry(retry=retry_if_exception_type(TransientError),
       wait=wait_exponential_jitter(initial=0.5, max=4.0),
       stop=stop_after_attempt(4), reraise=True)
async def _call_chat(messages: list[dict], model: str, *, stream: bool, max_completion_tokens: int | None, temperature: float) -> t.Any:
    async with _sem:
        client = _mk_client()
        try:
            return await client.chat.completions.create(
                model=model, messages=messages, temperature=temperature,
                max_completion_tokens=max_completion_tokens, stream=stream,
                timeout_ms=int(_TIMEOUT*1000),
            )
        except Exception as e:
            if _is_transient(e): raise TransientError(str(e))
            raise

async def groq_chat(messages: list[dict], *, model: str | None = None, temperature: float = 0.4, max_tokens: int | None = 800) -> str:
    model = model or _MODEL
    resp = await _call_chat(messages, model, stream=False, max_completion_tokens=max_tokens, temperature=temperature)
    return resp.choices[0].message.content or ""