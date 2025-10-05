#!/usr/bin/env python3
import sys, re
from pathlib import Path

HELPER = r'''
import logging

def _install_health_log_filter():
    try:
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        pass  # never break app on logging issues
'''
def patch_file(p: Path) -> bool:
    s = p.read_text(encoding="utf-8", errors="ignore")
    orig = s
    # normalize line endings
    s = s.replace('\r\n', '\n')

    # 1) inject helper if missing
    if "_install_health_log_filter" not in s:
        # insert after header imports (roughly after first 200 lines)
        lines = s.splitlines(keepends=True)
        idx = 0
        for i, ln in enumerate(lines[:200]):
            if ln.strip().startswith(("import ", "from ")):
                idx = i
        lines.insert(idx+1, HELPER + "\n")
        s = "".join(lines)

    # 2) ensure it's called in create_app()
    if "def create_app(" in s and not re.search(r"def\s+create_app\([^)]*\):[\s\S]{0,600}?_install_health_log_filter\(\)", s):
        def repl(m):
            return m.group(0) + "\n    _install_health_log_filter()\n"
        s2, n = re.subn(
            r"(def\s+create_app\([^)]*\):[\s\S]{0,400}?\n\s*app\s*=\s*Flask\([^)]*\))",
            repl, s, count=1, flags=re.M)
        if n == 0:
            s2, n = re.subn(
                r"(def\s+create_app\([^)]*\):)",
                r"\1\n    _install_health_log_filter()",
                s, count=1, flags=re.M)
        s = s2

    if s != orig:
        p.write_text(s, encoding="utf-8")
        return True
    return False

def main():
    if len(sys.argv) < 2:
        print("usage: patch_healthz.py <file1> [file2 ...]")
        return 2
    changed = 0
    for f in sys.argv[1:]:
        p = Path(f)
        if not p.exists():
            print(f"! missing: {p}")
            continue
        if patch_file(p):
            changed += 1
            print(f"+ patched: {p}")
        else:
            print(f"= unchanged: {p}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
