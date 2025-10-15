from typing import Optional
import base64, logging
log = logging.getLogger(__name__)

def _cfg(key, default=None):
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

def _b64(b: bytes) -> str:
    import base64 as _b; return _b.b64encode(b).decode()

def answer(image_bytes: bytes, prompt: str) -> str:
    provider = str(_cfg("VISION_PROVIDER", "none")).lower()
    if provider == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=_cfg("GEMINI_API_KEY"))
            model = genai.GenerativeModel(_cfg("GEMINI_MODEL","gemini-1.5-flash"))
            resp = model.generate_content([prompt, {"mime_type":"image/png","data": image_bytes}])
            return resp.text or "(kosong)"
        except Exception as e:
            log.exception("gemini vision error: %r", e); return f"[vision:gemini] error: {e!r}"
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=_cfg("OPENAI_API_KEY"))
            url = "data:image/png;base64," + _b64(image_bytes)
            res = client.chat.completions.create(model=_cfg("OPENAI_VISION_MODEL","gpt-4o-mini"),
                messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":url}}]}])
            return res.choices[0].message.content
        except Exception as e:
            log.exception("openai vision error: %r", e); return f"[vision:openai] error: {e!r}"
    return "[vision:none] Provider dimatikan."
