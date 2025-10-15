#!/usr/bin/env python3
'''scan_future_import_violations.py

Scans for modules where a `from __future__ import ...` line is present but
not at a valid top-of-file position (after docstring).

Exit code 0 if none found, 1 otherwise.
'''
from __future__ import annotations

import re
import sys
from pathlib import Path

def has_misplaced_future(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8", errors="surrogatepass")
    except Exception:
        return False
    lines = src.splitlines(keepends=True)

    fut_idxs = [i for i,l in enumerate(lines) if re.match(r'^\s*from\s+__future__\s+import\s+', l.replace("\\n", "").rstrip())]
    if not fut_idxs:
        return False

    def find_docstring_end(lines):
        i=0
        while i < len(lines):
            L = lines[i]
            if i==0 and L.startswith("#!"): i+=1; continue
            if re.match(r'^\s*#.*coding[:=]\s*[-\w.]+', L): i+=1; continue
            if L.strip().startswith("#") or L.strip()=="": i+=1; continue
            break
        if i >= len(lines): return 0
        stripped = lines[i].lstrip()
        t1 = "'"*3
        t2 = '"'*3
        if stripped.startswith(t1) or stripped.startswith(t2):
            if stripped.count(t1 if stripped.startswith(t1) else t2) >= 2: return i+1
            j=i+1
            while j < len(lines):
                if (t1 if stripped.startswith(t1) else t2) in lines[j]: return j+1
                j+=1
        return i

    allowed = find_docstring_end(lines)
    first = min(fut_idxs)
    return first > allowed

def scan(paths):
    violations = []
    for p in paths:
        P = Path(p)
        if P.is_file() and P.suffix==".py":
            if has_misplaced_future(P):
                violations.append(str(P))
        elif P.is_dir():
            for sub in P.rglob("*.py"):
                if has_misplaced_future(sub):
                    violations.append(str(sub))
    return violations

def main(argv):
    if len(argv) < 2:
        print("Usage: python scripts/scan_future_import_violations.py <dir_or_file> [...]")
        return 2
    v = scan(argv[1:])
    if v:
        print("Misplaced __future__ imports detected in:")
        for x in v:
            print(" -", x)
        return 1
    print("No misplaced __future__ imports found.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
