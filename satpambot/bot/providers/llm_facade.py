
import os, httpx

GROQ_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

ORDER = [s.strip() for s in (os.getenv("LLM_PROVIDER_ORDER","groq,gemini").split(",")) if s.strip()]
GROQ_MODEL = os.getenv("LLM_GROQ_MODEL","llama-3.1-8b-instant")
GEMINI_MODEL = os.getenv("LLM_GEMINI_MODEL","gemini-2.5-flash-lite")

async def _groq_chat(prompt: str, system: str | None = None, model: str | None = None, timeout=20):
    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY missing")
    model = model or GROQ_MODEL
    body = {
        "model": model,
        "messages": ([{"role":"system","content":system}] if system else []) + [
            {"role":"user","content": prompt}
        ],
    }
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=timeout) as x:
        r = await x.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
        if r.status_code != 200:
            raise RuntimeError(f"groq {r.status_code} {r.text}")
        j = r.json()
        return j["choices"][0]["message"]["content"].strip()

async def _gemini_chat(prompt: str, system: str | None = None, model: str | None = None, timeout=20):
    if not GOOGLE_KEY:
        raise RuntimeError("GOOGLE_API_KEY missing")
    model = model or GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_KEY}"
    parts = []
    if system:
        parts.append({"text": f"[SYSTEM]\n{system}"})
    parts.append({"text": prompt})
    body = {"contents":[{"role":"user","parts":parts}]}
    headers = {"Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=timeout) as x:
        r = await x.post(url, headers=headers, json=body)
        if r.status_code != 200:
            raise RuntimeError(f"gemini {r.status_code} {r.text}")
        j = r.json()
        text = j["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()

async def ask(prompt: str, *, system: str | None = None, provider_order: list[str] | None = None, prefer: str | None = None):
    """Satu pintu: ask(prompt, system=?). Fallback otomatis sesuai LLM_PROVIDER_ORDER."""
    order = provider_order or ORDER
    if prefer and prefer in order:
        order = [prefer] + [p for p in order if p != prefer]
    last_err = None
    for prov in order:
        try:
            if prov == "groq":
                return "groq", await _groq_chat(prompt, system)
            if prov == "gemini":
                return "gemini", await _gemini_chat(prompt, system)
        except Exception as e:
            last_err = e
    raise RuntimeError(f"all providers failed: {last_err}")
