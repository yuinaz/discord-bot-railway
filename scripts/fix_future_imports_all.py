#!/usr/bin/env python3
'''fix_future_imports_all.py

Rewrites Python files so `from __future__ import ...` lines are placed
at the earliest valid position (after optional shebang/encoding header
and the top-level module docstring, before any other statements).

Also normalizes accidental literal "\n" or stray whitespace on those lines.

Usage:
  python scripts/fix_future_imports_all.py <dir_or_file> [<more_paths> ...]

Notes:
- Idempotent: safe to run multiple times.
- Only rewrites files that actually contain a `from __future__` import.
- Makes a `.bak` copy next to each changed file (once per run).
'''
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

FUTURE_RE = re.compile(r'^\s*from\s+__future__\s+import\s+(.+)$')

def splitlines_keepends(s: str):
    return s.splitlines(keepends=True)

def find_docstring_block(lines):
    """If the file begins with a module docstring (after shebang/encoding/comments/blanks),
    return (start_line_idx, end_line_idx_inclusive). Otherwise return None.
    """
    i = 0
    # skip shebang & encoding cookie & leading comments/blanks
    while i < len(lines):
        line = lines[i]
        if i == 0 and line.startswith("#!"):
            i += 1
            continue
        if re.match(r'^\s*#.*coding[:=]\s*[-\w.]+', line):
            i += 1
            continue
        if line.strip().startswith("#") or line.strip() == "":
            i += 1
            continue
        break

    if i >= len(lines):
        return None

    # Approximate detection of leading triple-quoted docstring
    start = i
    l = lines[i].lstrip()
    t1 = "'"*3
    t2 = '"'*3
    if l.startswith(t1) or l.startswith(t2):
        delim = t1 if l.startswith(t1) else t2
        # if the opening line also closes
        if l.count(delim) >= 2:
            return (start, start)  # single-line docstring
        i += 1
        while i < len(lines):
            if delim in lines[i]:
                return (start, i)
            i += 1
        return None

    return None

def extract_future_imports(lines):
    """Return (imports, indices). `imports` are the raw imported feature chunks
    (e.g., ["annotations", "division as div"]) gathered from all lines.
    `indices` are the line numbers to remove.
    """
    imports = []
    idxs = []
    for i, line in enumerate(lines):
        m = FUTURE_RE.match(line.replace("\\n", "").rstrip())
        if m:
            idxs.append(i)
            raw = m.group(1)
            parts = [p.strip() for p in raw.split(",")]
            for p in parts:
                if p:
                    imports.append(p)
    return imports, idxs

def normalize_future_lines(features):
    if not features:
        return []
    seen = set()
    norm = []
    for f in features:
        if f not in seen:
            seen.add(f)
            norm.append(f)
    joined = ", ".join(norm)
    if len(joined) <= 96:
        return [f"from __future__ import {joined}\n"]
    out = []
    cur = []
    cur_len = 0
    for f in norm:
        seg = (", " if cur else "") + f
        if cur_len + len(seg) > 96:
            out.append("from __future__ import " + ", ".join(cur) + "\n")
            cur = [f]
            cur_len = len(f)
        else:
            cur.append(f)
            cur_len += len(seg)
    if cur:
        out.append("from __future__ import " + ", ".join(cur) + "\n")
    return out

def compute_insertion_index(lines):
    i = 0
    while i < len(lines):
        line = lines[i]
        if i == 0 and line.startswith("#!"):
            i += 1; continue
        if re.match(r'^\s*#.*coding[:=]\s*[-\w.]+', line):
            i += 1; continue
        if line.strip().startswith("#") or line.strip() == "":
            i += 1; continue
        break

    ds = find_docstring_block(lines)
    if ds:
        return ds[1] + 1
    return i

def fix_file(path: Path) -> bool:
    try:
        data = path.read_text(encoding="utf-8", errors="surrogatepass")
    except Exception:
        return False

    lines = splitlines_keepends(data)
    features, idxs = extract_future_imports(lines)
    if not features:
        return False

    insertion_idx = compute_insertion_index(lines)
    for i in sorted(idxs, reverse=True):
        del lines[i]

    new_future_lines = normalize_future_lines(features)
    lines[insertion_idx:insertion_idx] = new_future_lines

    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        try:
            bak.write_text(data, encoding="utf-8", errors="surrogatepass")
        except Exception:
            pass
    path.write_text("".join(lines), encoding="utf-8", errors="surrogatepass")
    return True

def iter_py_targets(paths):
    for p in paths:
        pth = Path(p)
        if pth.is_file() and pth.suffix == ".py":
            yield pth
        elif pth.is_dir():
            for sub in pth.rglob("*.py"):
                yield sub

def main(argv):
    if len(argv) < 2:
        print("Usage: python scripts/fix_future_imports_all.py <dir_or_file> [<more_paths> ...]")
        return 2
    any_changed = False
    for file in iter_py_targets(argv[1:]):
        try:
            changed = fix_file(file)
            if changed:
                print(f"[fixed] {file}")
                any_changed = True
        except Exception as e:
            print(f"[skip ] {file} ({e})")
    if not any_changed:
        print("No files needed fixing.")
    return 0

if __name__ == "__main__":
    import sys as _sys
    raise SystemExit(main(_sys.argv))
