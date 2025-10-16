
# llm_providers.py (v7.1)
import os, asyncio, subprocess, shlex, logging
from typing import Optional
logger = logging.getLogger(__name__)
def _env(k, default=None):
    v = os.getenv(k, default)
    if isinstance(v, str): return v.strip()
    return v
DEFAULT_GROQ_MODEL = _env("LLM_GROQ_MODEL", "llama-3.1-70b-versatile")
DEFAULT_GEMINI_MODEL = _env("LLM_GEMINI_MODEL", "gemini-1.5-flash")
DEFAULT_CLI_MODEL   = _env("LLM_CLI_MODEL", "gpt-4o-mini")
async def ask(prompt: str, system: Optional[str]=None, temperature: float=0.3) -> str:
    provider = _env("LLM_PROVIDER","auto").lower()
    if provider in ("auto","groq") and _env("GROQ_API_KEY"):
        txt = await _ask_groq(prompt, system, temperature)
        if txt: return txt
        if provider == "groq": return ""
    if provider in ("auto","gemini") and _env("GOOGLE_API_KEY"):
        txt = await _ask_gemini(prompt, system, temperature)
        if txt: return txt
        if provider == "gemini": return ""
    if provider in ("auto","cli"):
        txt = await _ask_cli(prompt, system, temperature)
        if txt: return txt
    return ""
async def _ask_groq(prompt, system, temperature):
    try:
        import httpx, json, os
        headers = {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"}
        body = {"model": DEFAULT_GROQ_MODEL, "messages": ([{"role":"system","content":system}] if system else []) + [{"role":"user","content":prompt}], "temperature": float(temperature)}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            return data.get("choices",[{}])[0].get("message",{}).get("content","").strip()
    except Exception as e:
        logger.info("[llm] groq failed: %r", e); return ""
async def _ask_gemini(prompt, system, temperature):
    try:
        import httpx, os
        model = DEFAULT_GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={os.environ['GOOGLE_API_KEY']}"
        parts = []
        if system: parts.append({"text": system})
        parts.append({"text": prompt})
        body = {"contents":[{"parts":parts}], "generationConfig":{"temperature": float(temperature)}}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            data = r.json()
            try: return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception: return ""
    except Exception as e:
        logger.info("[llm] gemini failed: %r", e); return ""
async def _ask_cli(prompt, system, temperature):
    cmd = f"llm -m {shlex.quote(DEFAULT_CLI_MODEL)} -t {float(temperature)}"
    if system: cmd += f" -s {shlex.quote(system)}"
    try:
        proc = await asyncio.create_subprocess_shell(cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, err = await proc.communicate(input=prompt.encode())
        if proc.returncode == 0: return out.decode().strip()
        logger.info("[llm] cli failed: %s", err.decode()[:200]); return ""
    except Exception as e:
        logger.info("[llm] cli call failed: %r", e); return ""
