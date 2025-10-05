#!/usr/bin/env python3
"""
apply_thread_exempt.py
---------------------------------
Unified & robust patcher:
  1) FIX existing guards that reference the wrong variable (e.g., 'message')
     by rebinding to the actual handler parameter name — for ALL matching
     functions in the file (not just the first).
  2) INSERT guard if missing, using the correct parameter name per function.

Scope:
  - Targets async handlers: on_message, on_message_edit
  - No ENV required, idempotent
  - Exempts discord.Thread and thread-like channel types

Usage:
    python patches/apply_thread_exempt.py
    python scripts/smoke_cogs.py
    git add -A && git commit -m "Hotfix: thread/forum exempt guard (robust)" && git push
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

def pick_param(func_name: str, args_str: str) -> str:
    names = []
    for raw in args_str.split(","):
        tok = raw.strip()
        if not tok:
            continue
        base = tok.split(":", 1)[0].split("=", 1)[0].strip().lstrip("*")
        if base in ("self", "cls", ""):
            continue
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

def build_guard(indent: str, var: str) -> str:
    return GUARD_TEMPLATE.format(indent=indent, var=var, mark=GUARD_MARK)

def insert_guard_once_in_func(text: str, func_name: str) -> tuple[str, bool]:
    # Insert guard inside the FIRST occurrence of the function (per file) only.
    pat = re.compile(
        rf"(async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n)(?P<indent>\s+)",
        re.S
    )
    def _repl(m):
        header = m.group(1)
        indent = m.group("indent")
        args_str = m.group("args")
        var = pick_param(func_name, args_str)
        guard = build_guard(indent, var)
        return f"{header}{guard}{indent}"
    new_text, n = pat.subn(_repl, text, count=1)
    return new_text, (n == 1)

def fix_existing_guards_in_file(text: str, func_name: str) -> tuple[str, int]:
    # Iterate ALL functions with this name in the file
    func_iter = list(re.finditer(
        rf"""
        (async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n)  # header
        (?P<body>(?:[ \t]+.*\n)*)                                        # body (simple)
        """, text, re.S | re.X
    ))
    fixed = 0
    for m in reversed(func_iter):  # reverse to keep offsets stable while replacing
        args_str = m.group("args")
        body = m.group("body")
        # find our marker in this body
        marker = re.search(rf"^(?P<indent>[ \t]+)# {re.escape(GUARD_MARK)}\s*$", body, re.M)
        if not marker:
            continue
        indent = marker.group("indent")
        var = pick_param(func_name, args_str)

        # operate on a small window after the marker (max ~40 lines) to be safe
        window_pat = re.compile(
            rf"""
            (^{re.escape(indent)}#\ {re.escape(GUARD_MARK)}\s*\n
            (?P<win>(?:^{re.escape(indent)}.*\n){{0,60}}))
            """, re.M
        )
        w = window_pat.search(body)
        if not w:
            continue
        win = w.group("win")
        # Replace any getattr(<ident>, "channel", ...) to use the correct 'var'
        win_new = re.sub(
            r'getattr\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"channel"',
            f'getattr({var}, "channel"',
            win
        )
        if win_new != win:
            new_body = body[:w.start("win")] + win_new + body[w.end("win"):]
            text = text[:m.start("body")] + new_body + text[m.end("body"):]
            fixed += 1
    return text, fixed

def patch_file(path: Path) -> tuple[bool, list[str]]:
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = path.read_text(encoding="utf-8", errors="ignore")
    changed = False
    touched = []

    # FIX phase: adjust any wrong variable names inside guards, for ALL matching functions
    total_fixed = 0
    for fn in FUNC_NAMES:
        src, nfixed = fix_existing_guards_in_file(src, fn)
        if nfixed:
            changed = True
            total_fixed += nfixed
            if fn not in touched:
                touched.append(fn)

    # INSERT phase: only if file has no guard marker at all
    if GUARD_MARK not in src:
        for fn in FUNC_NAMES:
            src2, did_ins = insert_guard_once_in_func(src, fn)
            if did_ins:
                changed = True
                if fn not in touched:
                    touched.append(fn)
                src = src2

    if changed:
        path.write_text(src, encoding="utf-8", newline="\n")
    return changed, touched

def main() -> int:
    if not COGS_DIR.exists():
        print(f"[ERROR] COGS directory not found: {COGS_DIR}")
        return 2

    total = 0
    modified = 0
    details = []
    for p in COGS_DIR.rglob("*.py"):
        if p.name == "__init__.py":
            continue
        total += 1
        ch, fns = patch_file(p)
        if ch:
            modified += 1
            details.append((p, fns))

    print(f"[OK] Scanned {total} files in {COGS_DIR}")
    print(f"[OK] Modified {modified} file(s).")
    for path, fns in details:
        print(f"  - {path.relative_to(REPO_ROOT)} ({', '.join(fns)})")
    if not modified:
        print("[INFO] Nothing to change (guards already correct or not applicable).")
    print("[TIP] Run: python scripts/smoke_cogs.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
