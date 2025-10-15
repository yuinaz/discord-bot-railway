#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compat patch v3 for embed_scribe:
- Works even if a legacy `class EmbedScribe` already exists and has a strict __init__.
- Appends a robust shim at the end of satpambot/bot/utils/embed_scribe.py that:
  * Defines _CompatEmbedScribe with __init__(*args, **kwargs)
  * Delegates .upsert() to module-level upsert() if present, else to the old class's upsert, else to write_embed()
  * Delegates .janitor() similarly or no-op
  * Finally sets: EmbedScribe = _CompatEmbedScribe  (overrides legacy)
Safe & idempotent: guarded by a sentinel.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "satpambot" / "bot" / "utils" / "embed_scribe.py"

APPEND = r"""
# ==== COMPAT PATCH (v3) — DO NOT EDIT ====
try:
    _ES_COMPAT_V3  # type: ignore[name-defined]
except NameError:
    _ES_COMPAT_V3 = True
    try:
        _OLD_EmbedScribe = EmbedScribe  # type: ignore[name-defined]
    except Exception:
        _OLD_EmbedScribe = None

    class _CompatEmbedScribe:
        def __init__(self, *args, **kwargs):
            # accept any init signature used by old callers
            self._init_args = args
            self._init_kwargs = kwargs

        async def upsert(self, *args, **kwargs):
            # Prefer new function-style API
            up = globals().get("upsert")
            if callable(up):
                return await up(*args, **kwargs)
            # Fallback to old class API if present
            if _OLD_EmbedScribe is not None:
                old_up = getattr(_OLD_EmbedScribe, "upsert", None)
                if callable(old_up):
                    try:
                        return await old_up(*args, **kwargs)
                    except TypeError:
                        # some old versions expect self; create a temp instance
                        tmp = _OLD_EmbedScribe()
                        return await old_up(tmp, *args, **kwargs)
            # Fallback to write_embed if available
            we = globals().get("write_embed")
            if callable(we):
                return await we(*args, **kwargs)
            raise RuntimeError("EmbedScribe compat v3: no upsert()/write_embed() found")

        async def janitor(self, *args, **kwargs):
            j = globals().get("janitor")
            if callable(j):
                return await j(*args, **kwargs)
            if _OLD_EmbedScribe is not None:
                old_j = getattr(_OLD_EmbedScribe, "janitor", None)
                if callable(old_j):
                    try:
                        return await old_j(*args, **kwargs)
                    except TypeError:
                        tmp = _OLD_EmbedScribe()
                        return await old_j(tmp, *args, **kwargs)
            return False

    # override any legacy class to guarantee flexible init
    EmbedScribe = _CompatEmbedScribe
# ==== END COMPAT PATCH (v3) ====
"""

def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: not found: {TARGET}")
        return 2
    txt = TARGET.read_text(encoding="utf-8", errors="ignore")
    if "_ES_COMPAT_V3" in txt:
        print("OK  : compat v3 already applied — nothing to do.")
        return 0
    TARGET.write_text(txt.rstrip() + "\n\n" + APPEND + "\n", encoding="utf-8")
    print("OK  : compat v3 appended to embed_scribe.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
