\
#!/usr/bin/env python3
# apply_no_dev_server_guard.py
from __future__ import annotations
"""
In-place guard: wrap Flask dev-server `app.run(...)` calls so they only run
when RUN_LOCAL_DEV=1 (for local development). In production (Render Free Plan)
these lines are skipped, preventing port conflicts and duplicate servers.
"""
import os, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root (assumes this file in /patches)

def patch_app_dashboard(p: pathlib.Path) -> bool:
    s = p.read_text(encoding="utf-8")
    if 'RUN_LOCAL_DEV' in s and 'app.run(' in s and '__name__' in s:
        return False
    pat = re.compile(r'^(?P<ind>[ \\t]*)app\\.run\\(\\s*host\\s*=\\s*"0\\.0\\.0\\.0"\\s*,\\s*port\\s*=\\s*_satp_port\\s*,\\s*debug\\s*=\\s*False\\s*\\)\\s*$', re.M)
    m = pat.search(s)
    if not m:
        return False
    ind = m.group('ind')
    repl = (
        f'{ind}# Hanya jalankan Flask dev server saat LOCAL DEV.\\n'
        f'{ind}import os\\n'
        f'{ind}if os.getenv("RUN_LOCAL_DEV", "0") == "1" and __name__ == "__main__":\\n'
        f'{ind}    app.run(host="0.0.0.0", port=_satp_port, debug=False)\\n'
    )
    s = s[:m.start()] + repl + s[m.end():]
    p.write_text(s, encoding="utf-8", newline="\\n")
    return True

def patch_web_safe_start(p: pathlib.Path) -> bool:
    s = p.read_text(encoding="utf-8")
    if 'RUN_LOCAL_DEV' in s and 'skip app.run(); prod web server handled by main.py.' in s:
        return False
    if 'import logging' not in s:
        s = s.replace('import os', 'import os, logging') if 'import os' in s else 'import os, logging\\n' + s
    pat = re.compile(r'^(?P<ind>[ \\t]*)app\\.run\\(\\s*host\\s*=\\s*host\\s*,\\s*port\\s*=\\s*port\\s*,\\s*use_reloader\\s*=\\s*False\\s*\\)\\s*$', re.M)
    m = pat.search(s)
    if not m:
        return False
    ind = m.group('ind')
    repl = (
        f'{ind}if os.getenv("RUN_LOCAL_DEV", "0") == "1":\\n'
        f'{ind}    app.run(host=host, port=port, use_reloader=False)\\n'
        f'{ind}else:\\n'
        f'{ind}    logging.getLogger(__name__).info(\\n'
        f'{ind}        "[web-safe-start] RUN_LOCAL_DEV!=1 -> skip app.run(); prod web server handled by main.py."\\n'
        f'{ind}    )\\n'
    )
    s = s[:m.start()] + repl + s[m.end():]
    p.write_text(s, encoding="utf-8", newline="\\n")
    return True

def main() -> int:
    repo = ROOT
    a = repo / "satpambot" / "dashboard" / "app_dashboard.py"
    b = repo / "satpambot" / "helpers" / "web_safe_start.py"

    changed = False
    if a.exists():
        if patch_app_dashboard(a):
            print(f"[OK] patched: {a}")
            changed = True
        else:
            print(f"[SKIP] nothing to patch or already patched: {a}")
    else:
        print(f"[MISS] not found: {a}")
    if b.exists():
        if patch_web_safe_start(b):
            print(f"[OK] patched: {b}")
            changed = True
        else:
            print(f"[SKIP] nothing to patch or already patched: {b}")
    else:
        print(f"[MISS] not found: {b}")
    if not changed:
        print("[NOTE] No changes were made.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
