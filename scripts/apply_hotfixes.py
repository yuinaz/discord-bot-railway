#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply hotfixes to SatpamBot repo (safe & idempotent).

Fixes ChatNeuroLite history unpack bug that caused:
  ValueError: not enough values to unpack (expected 3, got 2)

This script avoids nested triple quotes issues and only rewrites the single
problem line by transforming:

  history = "".join(f"{role}: {content}\n" for _,role,content in past)

into a tolerant form that accepts (ts, role, content) OR (role, content).
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGET = os.path.join(ROOT, "satpambot", "bot", "modules", "discord_bot", "cogs", "chat_neurolite.py")

NEW_BLOCK = (
    'history = "".join(\n'
    '    f"{(t[1] if len(t)==3 else t[0])}: {(t[2] if len(t)==3 else t[1])}\\n"\n'
    '    for t in past if isinstance(t,(list,tuple)) and len(t)>=2\n'
    ')\n'
)

def main():
    if not os.path.exists(TARGET):
        print("SKIP: chat_neurolite.py not found:", TARGET)
        return 0

    with open(TARGET, "r", encoding="utf-8") as f:
        src = f.read()

    # Quick check: if already patched (uses 'for t in past'), do nothing
    if "for t in past" in src and 'history = "".join(' in src:
        print("OK: already patched (detected 'for t in past').")
        return 0

    # Replace the exact generator pattern; tolerate spacing around commas
    lines = src.splitlines(True)
    changed = False
    for i, line in enumerate(lines):
        if "history" in line and "join(" in line and "past" in line and "content in past" in line:
            # the original line must reference 'for _, role, content in past' (with or without spaces)
            if "for _,role,content in past" in line or "for _, role, content in past" in line:
                indent = line[:len(line) - len(line.lstrip())]
                new_text = "".join(indent + l for l in NEW_BLOCK.splitlines(True))
                lines[i] = new_text
                changed = True
                break

    if not changed:
        print("SKIP: target pattern not found; no changes made.")
        return 0

    with open(TARGET, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))

    print("OK: chat_neurolite hotfix applied (history comprehension hardened).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
