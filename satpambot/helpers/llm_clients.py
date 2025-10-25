import os, asyncio
from typing import Optional

def _norm_base_groq() -> str:
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("GROQ_BASE_URL") or "https://api.groq.com"
    base = base.rstrip("/")
    return base if base.endswith("/openai/v1") else base + "/openai/v1"

class GeminiClient:
    def __init__(self, api_key: Optional[str]=None, model: Optional[str]=None, api_base: Optional[str]=None):
        self.key = api_key or os.getenv("GEMINI_API_KEY","")
        self.model = model or os.getenv("GEMINI_MODEL","gemini-1.5-flash")
        self.base = (api_base or os.getenv("GEMINI_API_BASE","https://generativelanguage.googleapis.com")).rstrip("/")
        self.timeout = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC","30"))
    def available(self) -> bool:
        return bool(self.key)
    async def answer(self, prompt: str, system: str) -> str:
        import httpx, json
        url = f"{self.base}/v1beta/models/{self.model}:generateContent?key={self.key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400},
        }
        if system:
            payload["systemInstruction"] = {"role": "system", "parts": [{"text": system}]}
        async with httpx.AsyncClient(timeout=self.timeout) as cx:
            r = await cx.post(url, json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"Gemini {r.status_code}: {r.text[:200]}")
            j = r.json()
            try:
                return (j["candidates"][0]["content"]["parts"][0]["text"] or "").strip()
            except Exception:
                try:
                    return (j["candidates"][0]["content"]["parts"][0].get("text","")).strip()
                except Exception:
                    raise RuntimeError("Gemini returned unexpected schema")

class GroqClient:
    def __init__(self, api_key: Optional[str]=None, model: Optional[str]=None):
        self.key = api_key or os.getenv("GROQ_API_KEY","")
        self.model = model or os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
        self.base = _norm_base_groq().rstrip("/")
        self.timeout = float(os.getenv("GROQ_HTTP_TIMEOUT_SEC","30"))
        self.url = f"{self.base}/chat/completions"
    def available(self) -> bool:
        return bool(self.key)
    async def answer(self, prompt: str, system: str) -> str:
        import httpx
        headers = {"Authorization": f"Bearer {self.key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4, "max_tokens": 400,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cx:
            r = await cx.post(self.url, headers=headers, json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"Groq {r.status_code}: {r.text[:200]}")
            j = r.json()
            try:
                return (j["choices"][0]["message"]["content"] or "").strip()
            except Exception:
                raise RuntimeError("Groq returned unexpected schema")

class QnaClient:
    """Gemini-first, Groq-fallback. Both via httpx; no openai sdk dependency."""
    def __init__(self):
        self.gemini = GeminiClient()
        self.groq = GroqClient()
    async def answer(self, prompt: str, system: str) -> str:
        if self.gemini.available():
            try:
                return await self.gemini.answer(prompt, system)
            except Exception as e:
                pass
        if self.groq.available():
            try:
                return await self.groq.answer(prompt, system)
            except Exception as e:
                pass
        return "(fallback) Maaf, aku belum bisa menjawab sekarang."
