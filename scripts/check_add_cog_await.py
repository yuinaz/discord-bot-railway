
from __future__ import annotations
import re
from pathlib import Path

SEARCH_DIRS = [
    Path("satpambot/bot/modules/discord_bot/cogs"),
    Path("modules/discord_bot/cogs"),
]

def scan_file(p: Path):
    s = p.read_text(encoding="utf-8", errors="ignore")
    bad = []
    pattern = re.compile(
        r"async\s+def\s+setup\s*\(\s*bot\s*.*?\)\s*:\s*(?:\n[ \t].*?)*(?=\n(?:async\s+def|def)\s|\Z)",
        re.DOTALL,
    )
    for m in pattern.finditer(s):
        block = m.group(0)
        for i, ln in enumerate(block.splitlines(), 1):
            if "bot.add_cog(" in ln and "await" not in ln.split("bot.add_cog(",1)[0]:
                bad.append(i)
    return bad

problems = []
for d in SEARCH_DIRS:
    if not d.exists(): continue
    for p in sorted(d.glob("*.py")):
        idxs = scan_file(p)
        if idxs:
            problems.append((p.as_posix(), idxs))

if not problems:
    print("[ok] No unawaited bot.add_cog() calls found inside setup()")
else:
    print("[WARN] Unawaited add_cog found:")
    for path, idxs in problems:
        print(f"- {path} : lines {idxs}")
