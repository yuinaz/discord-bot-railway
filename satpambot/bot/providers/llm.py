
"""
providers/llm.py
- API-only facade: chooses GROQ or GEMINI via ENV.
- GROQ_API_KEY and GOOGLE_API_KEY expected.
- OpenAI-compatible chat for Groq; Google Generative AI REST for Gemini text.
"""
import os, httpx, logging, json

log = logging.getLogger(__name__)

def _env(k, d=None): return os.getenv(k, d)

class LLM:
    def __init__(self):
        self.provider = _env("LLM_PROVIDER", "groq").lower()
        self.groq_key = _env("GROQ_API_KEY")
        self.groq_model = _env("GROQ_MODEL", "llama-3.1-8b-instant")
        self.gem_key = _env("GOOGLE_API_KEY")
        self.gem_model = _env("GEMINI_MODEL", "gemini-1.5-flash")
        self.timeout = float(_env("LLM_TIMEOUT_SEC", "15"))

    async def generate(self, system_prompt: str, messages: list, temperature: float = 0.6, max_tokens: int = 512):
        if self.provider == "groq":
            return await self._groq_chat(system_prompt, messages, temperature, max_tokens)
        return await self._gemini_text(system_prompt, messages, temperature, max_tokens)

    async def _groq_chat(self, system_prompt, messages, temperature, max_tokens):
        if not self.groq_key:
            return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}"}
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages or [])
        payload = {
            "model": self.groq_model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                log.warning("[llm:groq] %s %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            return (data.get("choices") or [{}])[0].get("message", {}).get("content")

    async def _gemini_text(self, system_prompt, messages, temperature, max_tokens):
        if not self.gem_key:
            return None
        # Gemini text via REST (text-only)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gem_model}:generateContent?key={self.gem_key}"
        parts = []
        if system_prompt:
            parts.append({"text": system_prompt})
        for m in messages or []:
            if m.get("role") == "user":
                parts.append({"text": m.get("content","")})
            elif m.get("role") == "assistant":
                parts.append({"text": m.get("content","")})
        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as cli:
            r = await cli.post(url, json=body)
            if r.status_code >= 400:
                log.warning("[llm:gemini] %s %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            candidates = data.get("candidates") or []
            if not candidates: return None
            parts = (candidates[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text","") for p in parts)
