#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

TARGET = Path('satpambot/bot/modules/discord_bot/cogs/anti_image_phash_runtime_strict.py')


def _insert_future_after_preamble(text: str) -> str:
    """
    Ensure a single `from __future__ import annotations` exists right after the
    (optional) module docstring and/or encoding line. Remove duplicates elsewhere.
    """
    # Drop every occurrence first
    text_wo_future, _ = re.subn(
        r'^\s*from\s+__future__\s+import\s+annotations\s*\n',
        '',
        text,
        flags=re.M,
    )

    pos = 0
    # Shebang at very top
    m = re.match(r'^#!.*\n', text_wo_future)
    if m:
        pos = m.end()

    # Encoding comment (PEP 263) — allowed before docstring
    m = re.match(r'^[ \t]*#.*coding[:=]\s*[-\w.]+\s*\n', text_wo_future[pos:])
    if m:
        pos += m.end()

    # Optional top-level docstring
    m = re.match(r'^[ \t]*([\'"]{3})(?:.|\n)*?\1\s*\n', text_wo_future[pos:])
    if m:
        pos += m.end()

    return text_wo_future[:pos] + 'from __future__ import annotations\n' + text_wo_future[pos:]


def main() -> int:
    if not TARGET.exists():
        print(f'[WARN] target not found: {TARGET}')
        return 0

    src = TARGET.read_text(encoding='utf-8', errors='ignore')
    fixed = _insert_future_after_preamble(src)

    if fixed != src:
        TARGET.write_text(fixed, encoding='utf-8', newline='\n')
        print(f'[OK] fixed __future__ import position in: {TARGET}')
    else:
        print(f'[OK] no changes needed: {TARGET}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
