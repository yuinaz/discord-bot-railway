#!/usr/bin/env python3
"""
apply_thread_exempt_v2.py
---------------------------------
Improved inserter that detects the actual parameter name in each handler and uses it in the guard.
This prevents NameError when the function doesn't use 'message' as the parameter.

Usage:
    python patches/apply_thread_exempt_v2.py
    python scripts/smoke_cogs.py
"""
from __future__ import annotations
import re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COGS_DIR = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"
GUARD_MARK = "THREAD/FORUM EXEMPTION — auto-inserted"

GUARD_TEMPLATE = """{indent}# {mark}
{indent}ch = getattr({var}, "channel", None)
{indent}if ch is not None:
{indent}    try:
{indent}        import discord
{indent}        if isinstance(ch, getattr(discord, "Thread", tuple())):
{indent}            return
{indent}        ctype = getattr(ch, "type", None)
{indent}        if ctype in {{
{indent}            getattr(discord.ChannelType, "public_thread", None),
{indent}            getattr(discord.ChannelType, "private_thread", None),
{indent}            getattr(discord.ChannelType, "news_thread", None),
{indent}        }}:
{indent}            return
{indent}    except Exception:
{indent}        pass
"""

FUNC_NAMES = ("on_message", "on_message_edit")

def pick_param(func_name: str, args_str: str) -> str:
    names = []
    for raw in args_str.split(","):
        tok = raw.strip()
        if not tok:
            continue
        base = tok.split(":", 1)[0].split("=", 1)[0].strip().lstrip("*")
        if base in ("self", "cls"):
            continue
        if base:
            names.append(base)
    if not names:
        return "message"
    if func_name == "on_message":
        for cand in ("message", "msg", "m"):
            if cand in names:
                return cand
        return names[0]
    if func_name == "on_message_edit":
        for cand in ("after", "message_after", "new", "updated", "message", "msg", "m"):
            if cand in names:
                return cand
        return names[-1]
    return names[0]

def insert_guard(content: str, func_name: str) -> tuple[str, bool]:
    if GUARD_MARK in content:
        # already inserted; skip (v2 is meant for fresh insertions)
        return content, False

    # capture header then body indent
    pat = re.compile(
        rf"(async\s+def\s+{func_name}\s*\((?P<args>.*?)\):\s*\n)(?P<indent>\s+)",
        re.S
    )
    def _repl(m: re.Match) -> str:
        header = m.group(1)
        indent = m.group("indent")
        args_str = m.group("args")
        var = pick_param(func_name, args_str)
        guard = GUARD_TEMPLATE.format(indent=indent, var=var, mark=GUARD_MARK)
        return f"{header}{guard}{indent}"
    new_content, n = pat.subn(_repl, content, count=1)
    return new_content, (n == 1)

def patch_file(path: Path) -> tuple[bool, list[str]]:
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = path.read_text(encoding="utf-8", errors="ignore")
    changed = False
    touched = []
    for fn in FUNC_NAMES:
        src2, did = insert_guard(src, fn)
        if did:
            changed = True
            touched.append(fn)
            src = src2
    if changed:
        path.write_text(src, encoding="utf-8", newline="\n")
    return changed, touched

def main() -> int:
    if not COGS_DIR.exists():
        print(f"[ERROR] COGS dir not found: {COGS_DIR}")
        return 2
    files = list(COGS_DIR.rglob("*.py"))
    total = 0
    mod = 0
    detail = []
    for p in files:
        if p.name == "__init__.py":
            continue
        total += 1
        ch, touched = patch_file(p)
        if ch:
            mod += 1
            detail.append((p, touched))
    print(f"[OK] Scanned {total} files in {COGS_DIR}")
    print(f"[OK] Patched {mod} file(s)")
    for p, fns in detail:
        print(f"  - {p.relative_to(REPO_ROOT)} ({', '.join(fns)})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
