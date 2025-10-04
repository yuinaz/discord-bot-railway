# patches/apply_no_dev_server_guard.py
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "satpambot" / "dashboard" / "app_dashboard.py",
    ROOT / "satpambot" / "helpers" / "web_safe_start.py",
]

def ensure_import(src: str, mod: str) -> str:
    # sisipkan "import <mod>" kalau belum ada
    if re.search(rf'^\s*import\s+{re.escape(mod)}\b', src, re.M):
        return src
    # taruh setelah future/encoding/header imports
    lines = src.splitlines(True)
    insert_at = 0
    while insert_at < len(lines) and (
        lines[insert_at].lstrip().startswith("#!") or
        lines[insert_at].lstrip().startswith("# -*-") or
        lines[insert_at].lstrip().startswith("from __future__")
    ):
        insert_at += 1
    # Lewati block import yang sudah ada
    while insert_at < len(lines) and lines[insert_at].strip().startswith(("import ", "from ")):
        insert_at += 1
    lines.insert(insert_at, f"import {mod}\n")
    return "".join(lines)

def guard_single_line_app_run(src: str, with_else_log: bool=False) -> str:
    """
    Bungkus baris `app.run(...)` satu baris dengan:
        if os.getenv("RUN_LOCAL_DEV","0") == "1":
            app.run(...)
    Jika with_else_log=True, tambahkan else dengan log info.
    """
    # kalau sudah pernah diguard, lewati
    if "RUN_LOCAL_DEV" in src and "app.run(" in src:
        return src

    pat = re.compile(r'^(?P<ind>[ \t]*)app\.run\((?P<args>[^()\n]*(?:\([^()\n]*\)[^()\n]*)*)\)\s*$',
                     re.M)
    def repl(m):
        ind = m.group("ind")
        args = m.group("args")
        if with_else_log:
            return (
                f'{ind}if os.getenv("RUN_LOCAL_DEV", "0") == "1":\n'
                f'{ind}    app.run({args})\n'
                f'{ind}else:\n'
                f'{ind}    import logging\n'
                f'{ind}    logging.getLogger(__name__).info('
                f'"[web-safe-start] RUN_LOCAL_DEV!=1 -> skip dev server (handled by main.py)")'
            )
        else:
            return (
                f'{ind}if os.getenv("RUN_LOCAL_DEV", "0") == "1":\n'
                f'{ind}    app.run({args})'
            )

    new_src, n = pat.subn(repl, src, count=1)
    return new_src if n else src

def patch_file(p: Path) -> bool:
    if not p.exists():
        print(f"[SKIP] missing: {p}")
        return False
    s = p.read_text(encoding="utf-8")
    orig = s

    s = ensure_import(s, "os")

    # app_dashboard.py -> guard sederhana tanpa else
    if p.name == "app_dashboard.py":
        s = guard_single_line_app_run(s, with_else_log=False)

    # web_safe_start.py -> guard + else log (biar jelas di prod)
    elif p.name == "web_safe_start.py":
        s = guard_single_line_app_run(s, with_else_log=True)

    if s != orig:
        p.write_text(s, encoding="utf-8", newline="\n")
        print(f"[OK] Patched: {p}")
        return True
    else:
        print(f"[OK] Already safe: {p}")
        return False

def main():
    any_change = False
    for f in FILES:
        any_change |= patch_file(f)
    if not any_change:
        print("[OK] Tidak ada perubahan (sudah aman).")

if __name__ == "__main__":
    main()
