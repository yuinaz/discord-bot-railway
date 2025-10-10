#!/usr/bin/env python3
"""
scripts/smoke_lint_thread_guard.py

Lint to ensure the thread/forum guard uses the correct variable names:
  - on_message: must use the handler's second param name (often 'message', but could be 'msg'/'m').
  - on_message_edit: must use 'after' (the updated message).

Fails (exit code 1) if a violation is detected. Safe to run on any repo state.
"""
from __future__ import annotations

import re, sys
from pathlib import Path

MARK = "THREAD/FORUM EXEMPTION — auto-inserted"

REPO_ROOT = Path(__file__).resolve().parents[1]
COGS_DIR = REPO_ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

def _param_names(args_str: str) -> list[str]:
    names = []
    for raw in args_str.split(","):
        tok = raw.strip()
        if not tok:
            continue
        base = tok.split(":", 1)[0].split("=", 1)[0].strip().lstrip("*")
        if base in ("self", "cls", ""):
            continue
        names.append(base)
    return names

def _iter_funcs(text: str, func_name: str):
    # Capture header + simple body (until dedent). This is an approximation but works for our guard-at-top style.
    pat = re.compile(
        rf"""
        (async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n)  # header
        (?P<body>(?:[ \t]+.*\n)*)                                        # body lines (same indent or deeper)
        """,
        re.S | re.X,
    )
    return list(pat.finditer(text))

def _guard_uses_var_near_marker(body: str, want_var: str, window_lines: int = 80) -> bool:
    # Find marker; then scan next N lines at same or deeper indent
    m = re.search(rf"^(?P<indent>[ \t]+)# {re.escape(MARK)}\s*$", body, re.M)
    if not m:
        # If no marker, we don't enforce; return True (pass) to avoid false negatives.
        return True
    indent = m.group("indent")
    # Slice window after marker
    tail = body[m.end():]
    lines = tail.splitlines(keepends=True)
    win = []
    for i, ln in enumerate(lines):
        if i >= window_lines:
            break
        # stop if dedented above the indent that started the guard
        if ln.strip() and not ln.startswith(indent):
            break
        win.append(ln)
    win_text = "".join(win)
    # Check correct usage exists, and *incorrect* 'message' usage does not conflict when want_var != 'message'
    ok = f'getattr({want_var}, "channel"' in win_text
    if want_var != "message" and 'getattr(message, "channel"' in win_text:
        return False
    return ok

def lint_file(p: Path) -> list[str]:
    try:
        src = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = p.read_text(encoding="utf-8", errors="ignore")
    errs: list[str] = []

    # on_message
    for m in _iter_funcs(src, "on_message"):
        args = _param_names(m.group("args"))
        if not args:
            continue
        var = args[0]  # after excluding self/cls, first param is the message-like object
        body = m.group("body")
        if not _guard_uses_var_near_marker(body, var):
            errs.append(f"on_message should use '{var}' near guard marker")

    # on_message_edit
    for m in _iter_funcs(src, "on_message_edit"):
        args = _param_names(m.group("args"))
        if not args:
            continue
        # typical signature: (before, after)
        want = "after" if "after" in args else args[-1]
        body = m.group("body")
        if not _guard_uses_var_near_marker(body, want):
            errs.append(f"on_message_edit should use '{want}' near guard marker")

    return errs

def main() -> int:
    if not COGS_DIR.exists():
        print(f"[ERROR] COGS directory not found: {COGS_DIR}")
        return 2

    total = 0
    bad = 0
    for p in sorted(COGS_DIR.rglob("*.py")):
        if p.name == "__init__.py":
            continue
        total += 1
        errs = lint_file(p)
        if errs:
            bad += 1
            print(f"[LINT] {p.relative_to(REPO_ROOT)}")
            for e in errs:
                print(f"  - {e}")

    if bad:
        print(f"✗ LINT FAILED: {bad} file(s) with guard issues (scanned {total} files).")
        return 1
    print(f"✓ LINT OK: scanned {total} files.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
