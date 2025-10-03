#!/usr/bin/env python3
"""
apply_thread_exempt.py
---------------------------------
Unified patcher:
  1) FIX existing guards (marker-based) that mistakenly reference `message`
     by rebinding to the actual handler parameter name.
  2) INSERT guard if missing, using the correct parameter name per function.

Scope:
  - Targets async handlers: on_message, on_message_edit
  - No ENV required, idempotent
  - Exempts discord.Thread and thread-like channel types

Usage:
    python patches/apply_thread_exempt.py
    python scripts/smoke_cogs.py
    git add -A && git commit -m "Hotfix: thread/forum exempt guard (unified)" && git push
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
        # most cogs: (before, after) — prefer "after"
        for cand in ("after", "message_after", "new", "updated", "message", "msg", "m"):
            if cand in names:
                return cand
        return names[-1]

    return names[0]

def build_guard(indent: str, var: str) -> str:
    return GUARD_TEMPLATE.format(indent=indent, var=var, mark=GUARD_MARK)

def insert_guard_once(content: str, func_name: str) -> tuple[str, bool]:
    # Find function header and first body indent
    pat = re.compile(
        rf"(async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n)(?P<indent>\s+)",
        re.S,
    )
    def _repl(m):
        header = m.group(1)
        indent = m.group("indent")
        args_str = m.group("args")
        var = pick_param(func_name, args_str)
        guard = build_guard(indent, var)
        return f"{header}{guard}{indent}"
    new_content, n = pat.subn(_repl, content, count=1)
    return new_content, (n == 1)

def fix_existing_guard(content: str, func_name: str) -> tuple[str, bool]:
    # Capture the whole function body to know its indent and args
    func_pat = re.compile(
        rf"""
        (async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n)  # header
        (?P<body>(?:[ \t]+.*\n)*)                                        # body (simple)
        """, re.S | re.X
    )
    m = func_pat.search(content)
    if not m:
        return content, False

    args_str = m.group("args")
    body = m.group("body")

    # Our marker line with leading indent
    marker_pat = re.compile(rf"^(?P<indent>[ \t]+)# {re.escape(GUARD_MARK)}\s*$", re.M)
    mm = marker_pat.search(body)
    if not mm:
        return content, False

    indent = mm.group("indent")
    var = pick_param(func_name, args_str)
    new_guard = build_guard(indent, var)

    # Replace the entire old guard block (from marker until a matching 'pass' at same indent)
    guard_block_pat = re.compile(
        rf"""
        ^{re.escape(indent)}#\ {re.escape(GUARD_MARK)}\s*\n  # marker
        (?:^{re.escape(indent)}.*\n)*?                         # lines inside guard
        ^{re.escape(indent)}pass\s*\n                         # closing pass at same indent
        """, re.M
    )
    new_body, n = guard_block_pat.subn(new_guard, body, count=1)
    if n == 0:
        # fallback: adjust getattr(var, "channel", ...) near marker
        near_range_pat = re.compile(
            rf"""
            (^{re.escape(indent)}#\ {re.escape(GUARD_MARK)}\s*\n
            (?:^{re.escape(indent)}.*\n){{0,30}})
            """, re.M
        )
        mm2 = near_range_pat.search(body)
        if mm2:
            seg = mm2.group(1)
            import re as _re
            seg2 = _re.sub(r'getattr\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"channel"', f'getattr({var}, "channel"', seg)
            new_body = body.replace(seg, seg2, 1)
            content = content[:m.start("body")] + new_body + content[m.end("body"):]
            return content, (seg != seg2)
        return content, False

    content = content[:m.start("body")] + new_body + content[m.end("body"):]
    return content, True

def patch_file(path: Path) -> tuple[bool, list[str]]:
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = path.read_text(encoding="utf-8", errors="ignore")
    changed = False
    touched = []

    # First try to FIX existing guards (if present)
    for fn in FUNC_NAMES:
        src2, did_fix = fix_existing_guard(src, fn)
        if did_fix:
            changed = True
            if fn not in touched:
                touched.append(fn)
            src = src2

    # Then, if not present at all, INSERT new guard
    if GUARD_MARK not in src:
        for fn in FUNC_NAMES:
            src2, did_ins = insert_guard_once(src, fn)
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
