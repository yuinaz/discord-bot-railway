#!/usr/bin/env python3
"""
Fix anti_image_phash_runtime_strict.py so it has:
- imports: os, time
- a single `_PHASH_REFRESH_SECONDS` definition (default 86400)
- a module-level `_last_phash_refresh` dict
- a `_phash_daily_gate(guild_id:int)` helper

This does NOT change logic elsewhere (no log injection). Idempotent.
"""
from __future__ import annotations
import re
from pathlib import Path

TARGET = Path("satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py")

HEADER_BLOCK = (
    "import os\n"
    "import time\n\n"
    "# pHash daily refresh window (env override-able)\n"
    "_PHASH_REFRESH_SECONDS = int(os.getenv(\"PHASH_REFRESH_SECONDS\", \"86400\"))  # default: 24 jam\n"
    "_last_phash_refresh: dict[int, float] = {}\n"
    "def _phash_daily_gate(guild_id: int) -> bool:\n"
    "    \"\"\"Return True if a refresh is allowed for this guild, at most once per _PHASH_REFRESH_SECONDS.\"\"\"\n"
    "    try:\n"
    "        now = time.time()\n"
    "    except Exception:\n"
    "        return True  # if time fails, never block\n"
    "    last = _last_phash_refresh.get(int(guild_id), 0.0)\n"
    "    if now - last < _PHASH_REFRESH_SECONDS:\n"
    "        return False\n"
    "    _last_phash_refresh[int(guild_id)] = now\n"
    "    return True\n"
)

def ensure_header_bits(src: str) -> str:
    # 1) Ensure `import os` and `import time`
    lines = src.splitlines(True)
    insert_at = 0

    # Skip shebang at very top
    if insert_at < len(lines) and lines[insert_at].lstrip().startswith("#!"):
        insert_at += 1
    # Skip encoding
    if insert_at < len(lines) and "coding" in lines[insert_at]:
        insert_at += 1
    # Skip leading triple-double-quote docstring if present
    if insert_at < len(lines) and lines[insert_at].lstrip().startswith(\"\"\"\"):
        quote = \"\"\"\"
        insert_at += 1
        while insert_at < len(lines):
            if lines[insert_at].rstrip().endswith(quote):
                insert_at += 1
                break
            insert_at += 1

    # Remove any existing conflicting definitions to avoid duplicates
    src = re.sub(r'(?m)^\s*_PHASH_REFRESH_SECONDS\s*=.*\n', '', src)
    src = re.sub(r'(?ms)^\s*_last_phash_refresh\s*:\s*dict\[int,\s*float\]\s*=\s*\{\}\s*\n', '', src)
    src = re.sub(r'(?ms)^\s*def\s+_phash_daily_gate\s*\(\s*guild_id\s*:\s*int\s*\)\s*->\s*bool\s*:\s*.*?\n(?=^\S|\Z)', '', src)

    # Ensure import os/time exist somewhere; we'll add in header block anyway, then dedupe
    new_src = "".join(lines[:insert_at]) + HEADER_BLOCK + "\n\n" + "".join(lines[insert_at:])

    # De-duplicate simple duplicate import lines
    seen = set()
    deduped_lines = []
    for ln in new_src.splitlines(True):
        if ln.strip() in ("import os", "import time"):
            key = ln.strip()
            if key in seen:
                continue
            seen.add(key)
        deduped_lines.append(ln)
    return "".join(deduped_lines)

def main():
    if not TARGET.exists():
        print(f"[ERROR] File not found: {TARGET}")
        return 2
    src = TARGET.read_text(encoding="utf-8")
    new_src = ensure_header_bits(src)
    if new_src != src:
        TARGET.write_text(new_src, encoding="utf-8", newline="\n")
        print(f"[OK] Patched: {TARGET.as_posix()}")
    else:
        print("[OK] No change needed (already OK).")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
