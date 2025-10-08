
from __future__ import annotations

"""
Lightweight translation utilities for SatpamBot.

Providers:
- deep-translator (GoogleTranslator)  -> default
- googletrans-py                       -> fallback/optional

This module has zero runtime dependency on OpenAI.
"""

from typing import Optional, Literal

try:
    # googletrans-py package uses the import name "googletrans"
    from googletrans import Translator as _GTTranslator  # type: ignore
    _HAS_GOOGLETRANS = True
except Exception:  # pragma: no cover
    _HAS_GOOGLETRANS = False
    _GTTranslator = None  # type: ignore

try:
    from deep_translator import GoogleTranslator as _DTGoogleTranslator  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("deep-translator is required for translate_utils") from e

try:
    from langdetect import detect as _detect_lang  # type: ignore
except Exception:  # pragma: no cover
    def _detect_lang(text: str) -> str:
        # minimal heuristic fallback
        return "en"


Provider = Literal["auto", "deep", "googletrans"]


def detect_lang(text: str) -> str:
    """Detect language code (very fast, best-effort)."""
    try:
        return _detect_lang(text)
    except Exception:
        # default to English if detector fails
        return "en"


def translate_text(
    text: str,
    target: str = "en",
    provider: Provider = "auto",
    source: Optional[str] = None,
) -> str:
    """
    Translate `text` to `target` using selected provider.
    - provider="auto" picks googletrans if available, else deep-translator
    - source=None means auto-detect
    """
    text = (text or "").strip()
    if not text:
        return ""

    selected: Provider = provider
    if provider == "auto":
        selected = "googletrans" if _HAS_GOOGLETRANS else "deep"

    if selected == "googletrans":
        if not _HAS_GOOGLETRANS:
            # silently fall back to deep if googletrans not installed
            selected = "deep"
        else:
            try:
                tr = _GTTranslator()
                res = tr.translate(text, dest=target, src=source or "auto")
                return getattr(res, "text", str(res))
            except Exception:
                # if googletrans fails at runtime, fall back
                selected = "deep"

    # deep-translator path
    src = source if (source and source != "auto") else "auto"
    try:
        return _DTGoogleTranslator(source=src, target=target).translate(text)
    except Exception as e:
        # don't explode—return original text as last resort
        return text
