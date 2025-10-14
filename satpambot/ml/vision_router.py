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
<<<<<<< HEAD
    provider = str(_cfg("VISION_PROVIDER", "gemini")).lower().strip()

    # --- Gemini (new SDK) ---
    if provider == "gemini":
        try:
            try:
                from satpambot.ai.gemini_client import generate_vision
                model = _cfg("GEMINI_MODEL", "gemini-2.5-flash")
                return generate_vision(image_bytes, prompt, model=model) or "(kosong)"
            except Exception:
                from google import genai
                api_key = _cfg("GEMINI_API_KEY") or _cfg("GOOGLE_API_KEY")
                client = genai.Client(api_key=api_key) if api_key else genai.Client()
                payload = [prompt, {"mime_type":"image/png", "data": image_bytes}]
                resp = client.models.generate_content(model=_cfg("GEMINI_MODEL", "gemini-2.5-flash"), contents=payload)
                return getattr(resp, "text", None) or "(kosong)"
        except Exception as e:
            log.exception("gemini vision error: %r", e); return f"[vision:gemini] error: {e!r}"

    # --- OpenAI (legacy; optional) ---
=======
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
>>>>>>> ef940a8 (heal)
    if provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=_cfg("OPENAI_API_KEY"))
            url = "data:image/png;base64," + _b64(image_bytes)
<<<<<<< HEAD
            res = client.chat.completions.create(
                model=_cfg("OPENAI_VISION_MODEL","gpt-4o-mini"),
                messages=[
                    {"role":"system","content":"You are a helpful vision assistant."},
                    {"role":"user","content":[
                        {"type":"text","text": prompt},
                        {"type":"image_url","image_url":{"url": url}}
                    ]}
                ]
            )
            return res.choices[0].message.content
        except Exception as e:
            log.exception("openai vision error: %r", e); return f"[vision:openai] error: {e!r}"

    return f"[vision] unknown provider: {provider!r}"
=======
            res = client.chat.completions.create(model=_cfg("OPENAI_VISION_MODEL","gpt-4o-mini"),
                messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":url}}]}])
            return res.choices[0].message.content
        except Exception as e:
            log.exception("openai vision error: %r", e); return f"[vision:openai] error: {e!r}"
    return "[vision:none] Provider dimatikan."
>>>>>>> ef940a8 (heal)
