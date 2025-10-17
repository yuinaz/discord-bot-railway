# -*- coding: utf-8 -*-
"""
Patch: _ask_groq with user default model llama-3.1-8b-instant.
Override via env LLM_GROQ_MODEL if needed.
"""
import os, json, logging, httpx

logger = logging.getLogger(__name__)
DEFAULT_GROQ_MODEL = os.environ.get("LLM_GROQ_MODEL", "llama-3.1-8b-instant")

async def _ask_groq(prompt, system=None, temperature=0.2):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        }
        msgs = []
        if system:
            msgs.append({"role": "system", "content": str(system)})
        msgs.append({"role": "user", "content": str(prompt)})
        payload = {
            "model": DEFAULT_GROQ_MODEL,
            "messages": msgs,
            "temperature": float(temperature),
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=payload)
            if r.status_code >= 400:
                logger.warning("[llm] groq 4xx: %s", r.text[:500])
                r.raise_for_status()
            data = r.json()
            return (data.get("choices") or [{}])[0].get("message",{}).get("content","").strip()
    except Exception as e:
        logger.info("[llm] groq failed: %r", e)
        return ""
