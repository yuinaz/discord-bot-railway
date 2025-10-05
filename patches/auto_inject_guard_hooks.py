# -*- coding: utf-8 -*-
"""
Auto-inject Guard Hooks
-----------------------
Menyuntikkan `from satpambot.ml import guard_hooks` + try/except ke `on_message` guard-image
secara aman. Menghindari file non-guard & file bootstrap tertentu.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root (../)
COGS = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

EXCLUDE = {
    "anti_url_phish_guard.py",
    "anti_url_phish_guard_bootstrap.py",
}

def needs_inject(text: str) -> bool:
    return "from satpambot.ml import guard_hooks" not in text

def is_guard_candidate(name: str, text: str) -> bool:
    base = name.lower()
    if base in EXCLUDE:
        return False
    # heuristik: hanya image-related atau yang sudah disepakati di proyek
    keys = ("image", "phash", "attach", "ocr", "phish_hash", "scored_guard")
    return any(k in base for k in keys) and "async def on_message" in text

def inject(text: str) -> str:
    # 1) sisipkan import kalau belum ada
    if needs_inject(text):
        text = re.sub(r"^(from __future__.+?\n)?", lambda m: (m.group(0) or "") + "from satpambot.ml import guard_hooks\n", text, count=1, flags=re.MULTILINE)
    # 2) bungkus body on_message dengan try/except ringan
    def repl(m: re.Match[str]) -> str:
        header = m.group("def")
        body = m.group("body")
        # kalau sudah ada guard_hooks.on_guard_error, skip
        if "guard_hooks.on_guard_error(" in body:
            return m.group(0)
        wrapped = (
            f"{header}:\n"
            "        try:\n"
            f"{body}"
            "        except Exception as e:\n"
            "            try:\n"
            "                guard_hooks.on_guard_error(e, context='on_message')\n"
            "            except Exception:\n"
            "                pass\n"
        )
        return wrapped
    pattern = re.compile(r"(?P<def>\s*async\s+def\s+on_message\(self,\s*message[^)]*\)):\n(?P<body>(\s{8}.+\n)+)", re.MULTILINE)
    return pattern.sub(repl, text)

def main() -> int:
    if not COGS.exists():
        print("Skip: cogs dir not found", file=sys.stderr)
        return 0
    changed = 0
    for p in sorted(COGS.glob("*.py")):
        name = p.name
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            print(f"Skip (read error): {name}")
            continue
        if not is_guard_candidate(name, text):
            print(f"Skip (non-image guard): {name}")
            continue
        new_text = inject(text)
        if new_text != text:
            p.write_text(new_text, encoding="utf-8")
            print(f"Injected: {name}")
            changed += 1
        else:
            print(f"Skip (already injected): {name}")
    print(f"Done. Files injected: {changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
