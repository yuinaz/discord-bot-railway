"""Lightweight translation helper with multi-provider fallback.
Safe to import in smoke tests (no heavy imports at module level).
"""

from __future__ import annotations
from typing import Optional

# Lazy import providers to keep import safe for smoke tests.
def _try_googletrans(text: str, target: str, source: str) -> Optional[str]:
    try:
        from googletrans import Translator  # type: ignore
    except Exception:
        return None
    try:
        t = Translator()
        res = t.translate(text, src=source, dest=target)
        return getattr(res, "text", None)
    except Exception:
        return None


def _try_deeptranslator(text: str, target: str, source: str) -> Optional[str]:
    try:
        from deep_translator import GoogleTranslator  # type: ignore
    except Exception:
        return None
    try:
        # deep_translator uses 'source/target' naming and expects 'auto' or lang codes
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception:
        return None


_LANG_ALIAS = {
    "bahasa": "id",
    "indonesian": "id",
    "jp": "ja",
    "jpn": "ja",
    "zh": "zh-CN",
    "cn": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "en-us": "en",
    "en-gb": "en",
}

def _norm_lang(code: str) -> str:
    code = (code or "").strip()
    if not code:
        return "auto"
    key = code.lower()
    return _LANG_ALIAS.get(key, code)


def translate_text(text: str, target_lang: str = "id", source_lang: str = "auto") -> str:
    """Translate *text* to *target_lang*, falling back across providers.
    Raises RuntimeError if all providers fail.
    """
    if not isinstance(text, str):
        raise TypeError("text must be str")
    text = text.strip()
    if not text:
        return ""

    target = _norm_lang(target_lang)
    source = _norm_lang(source_lang)

    # Provider order: googletrans -> deep_translator
    for provider in (_try_googletrans, _try_deeptranslator):
        out = provider(text, target, source)
        if isinstance(out, str) and out.strip():
            return out

    raise RuntimeError("No translation provider available or all failed")


__all__ = ["translate_text"]
