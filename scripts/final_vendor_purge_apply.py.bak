from __future__ import annotations

# scripts/final_vendor_purge_apply.py
"""
Edits in-place to remove legacy vendor tokens from:
- chat_neurolite.py  (drop optional vendor import block, remove OPENAI_* lines)
- auto_update_manager.py  (replace 'openai' word with 'groq')

Run:
    python -m scripts.final_vendor_purge_apply
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def patch_chat_neurolite() -> str:
    p = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "chat_neurolite.py"
    if not p.exists():
        return "[SKIP] chat_neurolite.py not found"
    s = p.read_text(encoding="utf-8", errors="replace")
    before = s

    # Remove the optional vendor import block entirely (try/except that imports from 'openai')
    s = re.sub(
        r"\ntry:\s*\n\s*#.*OpenAI[^\n]*\n(?:.*\n){0,8}?_HAS_OPENAI\s*=\s*True.*?\n\s*except\s+Exception:\s*\n\s*_HAS_OPENAI\s*=\s*False.*?\n",
        "\n",
        s,
        flags=re.I
    )

    # Remove any lines that still mention OPENAI_* keys
    s = re.sub(r".*OPENAI[^\\n]*\\n", "", s, flags=re.I)

    # Safety: remove lines with 'gpt-' literals if any remain
    s = re.sub(r".*gpt-.*\\n", "", s, flags=re.I)

    if s != before:
        p.write_text(s, encoding="utf-8")
        return "[OK] chat_neurolite.py cleaned"
    return "[INFO] chat_neurolite.py already clean"

def patch_auto_update_manager() -> str:
    p = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "auto_update_manager.py"
    if not p.exists():
        return "[SKIP] auto_update_manager.py not found"
    s = p.read_text(encoding="utf-8", errors="replace")
    before = s

    # Replace 'openai' word with 'groq' in a safe, case-insensitive manner
    s = re.sub(r"\\bopenai\\b", "groq", s, flags=re.I)

    if s != before:
        p.write_text(s, encoding="utf-8")
        return "[OK] auto_update_manager.py cleaned"
    return "[INFO] auto_update_manager.py already clean"

def main():
    print(patch_chat_neurolite())
    print(patch_auto_update_manager())

if __name__ == "__main__":
    main()
