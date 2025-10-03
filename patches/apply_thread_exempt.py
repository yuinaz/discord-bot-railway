#!/usr/bin/env python3
"""
apply_thread_exempt.py
---------------------------------
Hotfix patcher to EXEMPT any Thread/Forum messages from *autoban* paths.
- Safe: idempotent (won't double-insert).
- No ENV required.
- Targets any cog that implements `async def on_message(...)` or `async def on_message_edit(...)`.
- Inserts an early-return guard for discord Threads (and thread channel types).
Usage:
    python patches/apply_thread_exempt.py
    python scripts/smoke_cogs.py   # optional check
    git add -A && git commit -m "Hotfix: exempt thread/forum from autoban (no-ENV)" && git push
"""
import re
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COGS_DIR = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

GUARD_MARK = "THREAD/FORUM EXEMPTION — auto-inserted"

GUARD_BLOCK_TEMPLATE = """{indent}# {mark}
{indent}ch = getattr(message, "channel", None)
{indent}if ch is not None:
{indent}    try:
{indent}        import discord
{indent}        # Exempt true Thread objects
{indent}        if isinstance(ch, getattr(discord, "Thread", tuple())):
{indent}            return
{indent}        # Exempt thread-like channel types (public/private/news threads)
{indent}        ctype = getattr(ch, "type", None)
{indent}        if ctype in {{
{indent}            getattr(discord.ChannelType, "public_thread", None),
{indent}            getattr(discord.ChannelType, "private_thread", None),
{indent}            getattr(discord.ChannelType, "news_thread", None),
{indent}        }}:
{indent}            return
{indent}    except Exception:
{indent}        # If discord import/type checks fail, do not block normal flow
{indent}        pass
"""

FUNC_NAMES = ("on_message", "on_message_edit")

def insert_guard_once(content: str, func_name: str) -> tuple[str, bool]:
    if GUARD_MARK in content:
        return content, False

    # Match the start of the async handler function and capture the first line's indentation
    pattern = re.compile(
        rf"(async\s+def\s+{func_name}\s*\(.*?\):\s*\n)(\s+)",
        flags=re.S
    )

    def _repl(m: re.Match) -> str:
        header = m.group(1)  # 'async def ...:\n'
        indent = m.group(2)  # indentation of first line in function body
        guard = GUARD_BLOCK_TEMPLATE.format(indent=indent, mark=GUARD_MARK)
        # Put header back, then the guard, then restore the original indent
        return f"{header}{guard}{indent}"

    new_content, n = pattern.subn(_repl, content, count=1)
    return new_content, (n == 1)

def patch_file(path: Path) -> tuple[bool, list[str]]:
    changed = False
    applied_to = []
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        original = path.read_text(encoding="utf-8", errors="ignore")

    content = original
    for fn in FUNC_NAMES:
        content, did = insert_guard_once(content, fn)
        if did:
            changed = True
            applied_to.append(fn)

    if changed:
        path.write_text(content, encoding="utf-8", newline="\n")
    return changed, applied_to

def main() -> int:
    if not COGS_DIR.exists():
        print(f"[ERROR] COGS directory not found: {COGS_DIR}")
        return 2

    total_files = 0
    modified_files = 0
    changes_detail = []

    # Search broadly: any .py under cogs that likely process messages
    candidates = list(COGS_DIR.rglob("*.py"))
    # Prefer cogs that look like guards/antispam/anti-image/phish/autoban
    def _score(p: Path) -> int:
        n = p.name.lower()
        keywords = ["anti", "guard", "ban", "phish", "image", "invite", "nsfw", "link"]
        return sum(k in n for k in keywords)
    candidates.sort(key=_score, reverse=True)

    for p in candidates:
        if p.name == "__init__.py":
            continue
        total_files += 1
        changed, applied_to = patch_file(p)
        if changed:
            modified_files += 1
            changes_detail.append((p, applied_to))

    print(f"[OK] Scanned {total_files} files in {COGS_DIR}")
    if modified_files:
        print(f"[OK] Patched {modified_files} file(s):")
        for path, funcs in changes_detail:
            print(f"  - {path.relative_to(REPO_ROOT)}  (inserted guard in: {', '.join(funcs)})")
        print(f"[TIP] Run: python scripts/smoke_cogs.py")
        return 0
    else:
        print("[INFO] No changes needed (guard already present or no matching handlers).")
        return 0

if __name__ == "__main__":
    sys.exit(main())
