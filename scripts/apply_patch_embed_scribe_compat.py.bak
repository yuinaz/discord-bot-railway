#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply a tiny compatibility shim into satpambot/bot/utils/embed_scribe.py:
- If the module doesn't define `class EmbedScribe`, append a wrapper class that
  delegates to the module-level `upsert()` (or `write_embed()` fallback).
Safe, idempotent, and keeps your existing logic intact.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "satpambot" / "bot" / "utils" / "embed_scribe.py"

CLASS_SNIPPET = """
# ---- BACK-COMPAT SHIM (auto-appended) ----
try:
    _ES_SENTINEL  # type: ignore[name-defined]
except NameError:
    _ES_SENTINEL = True
    class EmbedScribe:
        @staticmethod
        async def upsert(bot, channel, embed, key=None, pin=True, thread_name=None, **kwargs):
            # Delegate to new function-style API if present
            try:
                up = globals().get("upsert")
                if up:
                    return await up(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
            except Exception:
                pass
            # Fallback to older API name if available
            we = globals().get("write_embed")
            if we:
                return await we(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
            raise RuntimeError("EmbedScribe shim: no upsert()/write_embed() in embed_scribe module")

        @staticmethod
        async def janitor(channel, key=None, **kwargs):
            j = globals().get("janitor")
            if j:
                return await j(channel, key=key, **kwargs)
            return False
# ---- END BACK-COMPAT SHIM ----
"""

def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: file not found: {TARGET}")
        return 2
    txt = TARGET.read_text(encoding="utf-8", errors="ignore")
    if "class EmbedScribe" in txt:
        print("OK  : EmbedScribe already present — nothing to do.")
        return 0
    # Append shim
    TARGET.write_text(txt.rstrip() + "\n\n" + CLASS_SNIPPET, encoding="utf-8")
    print("OK  : Back-compat EmbedScribe appended to embed_scribe.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
