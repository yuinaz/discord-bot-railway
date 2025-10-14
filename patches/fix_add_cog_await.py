
from __future__ import annotations
import re, sys
from pathlib import Path

SEARCH_DIRS = [
    Path("satpambot/bot/modules/discord_bot/cogs"),
    Path("modules/discord_bot/cogs"),
]

def fix_file(p: Path) -> bool:
    s = p.read_text(encoding="utf-8")
    orig = s
    def repl_block(m: re.Match) -> str:
        block = m.group(0)
        lines = block.splitlines()
        for i, ln in enumerate(lines):
            if "bot.add_cog(" in ln and "await" not in ln.split("bot.add_cog(",1)[0]:
                lines[i] = ln.replace("bot.add_cog(", "await bot.add_cog(")
        return "\n".join(lines)
    pattern = re.compile(
        r"async\s+def\s+setup\s*\(\s*bot\s*.*?\)\s*:\s*(?:\n[ \t].*?)*(?=\n(?:async\s+def|def)\s|\Z)",
        re.DOTALL,
    )
    s = pattern.sub(repl_block, s)
    if s != orig:
        p.write_text(s, encoding="utf-8")
        print(f"[fixed] {p}")
        return True
    return False

def main():
    any_change = False
    for d in SEARCH_DIRS:
        if not d.exists(): 
            continue
        for p in sorted(d.glob("*.py")):
            try:
                any_change |= fix_file(p)
            except Exception as e:
                print(f"[error] {p}: {e}")
    if not any_change:
        print("[info] No changes needed (all setup() already awaiting add_cog).")
    else:
        print("[done] Applied awaiting fixes.")
    print("Next: restart or /repo_pull_and_restart")

if __name__ == "__main__":
    main()
