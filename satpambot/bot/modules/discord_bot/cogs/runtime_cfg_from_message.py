#!/usr/bin/env python3
"""
scripts/smoke_lint_thread_guard.py

Lint memastikan thread/forum guard pakai variabel yang benar:
- on_message: pakai nama param handler (biasanya 'message')
- on_message_edit: pakai 'after'

Catatan fix: parser body fungsi sekarang berhenti saat dedent relatif
indentasi body, jadi tidak lagi “menyedot” dekorator/def berikutnya.
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

def _iter_func_blocks(text: str, func_name: str):
    """Yield dicts: {'args': str, 'body': str} for each async def func_name(...):."""
    # header match
    hdr = re.compile(
        rf'^([ \t]*)async\s+def\s+{func_name}\s*\((?P<args>.*?)\)\s*:\s*\n',
        re.M | re.S
    )
    pos = 0
    out = []
    while True:
        m = hdr.search(text, pos)
        if not m:
            break
        base_indent = m.group(1)               # indent level of "def" inside class
        body_start = m.end()
        # Find first non-empty line to determine body indent
        m_first = re.search(r'^(?P<i>[ \t]+)\S', text[body_start:], re.M)
        if not m_first:
            # empty body? treat as none
            out.append({'args': m.group('args'), 'body': ""})
            pos = body_start
            continue
        body_indent = m_first.group('i')       # indent of first statement in body

        # Now consume until a line dedented < body_indent
        lines = text[body_start:].splitlines(True)
        kept = []
        for ln in lines:
            if ln.strip() and not ln.startswith(body_indent):
                break
            kept.append(ln)
        body = "".join(kept)
        out.append({'args': m.group('args'), 'body': body})
        pos = body_start + sum(len(x) for x in kept)
    return out

def _guard_ok(body: str, want_var: str) -> bool:
    # If no marker -> pass (we only lint guards that ada markernya)
    m = re.search(rf'^(?P<ind>[ \t]+)# {re.escape(MARK)}\s*$', body, re.M)
    if not m:
        return True
    ind = m.group('ind')
    tail = body[m.end():]
    # Walk lines in same guard block (same indent or deeper)
    ok = False
    for ln in tail.splitlines():
        if ln.strip() and not ln.startswith(ind):
            break
        if 'getattr(' in ln and '"channel"' in ln:
            if f'getattr({want_var}, "channel"' in ln:
                ok = True
            # If target bukan 'message', pastikan nggak ada sisa 'message'
            if want_var != "message" and 'getattr(message, "channel"' in ln:
                return False
    return ok

def lint_file(p: Path) -> list[str]:
    try:
        src = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = p.read_text(encoding="utf-8", errors="ignore")
    errs: list[str] = []

    # on_message
    for fn in _iter_func_blocks(src, "on_message"):
        args = _param_names(fn['args'])
        if not args:
            continue
        want = args[0]
        if not _guard_ok(fn['body'], want):
            errs.append(f"on_message should use '{want}' near guard marker")

    # on_message_edit
    for fn in _iter_func_blocks(src, "on_message_edit"):
        args = _param_names(fn['args'])
        if not args:
            continue
        want = "after" if "after" in args else args[-1]
        if not _guard_ok(fn['body'], want):
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
