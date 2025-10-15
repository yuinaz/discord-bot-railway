# -*- coding: utf-8 -*-
"""
scripts/cleanup_duplicates.py
Hapus folder/file duplikat umum yang bikin kebaca ganda.
Dry-run: python scripts/cleanup_duplicates.py
Apply  : python scripts/cleanup_duplicates.py --apply
"""
import os, shutil, sys
from pathlib import Path

PLAN = [
    ("satpambot/dashboard/templates/templates", "dir"),
    ("bot", "dir"),
]

def main():
    apply = "--apply" in sys.argv
    for p, kind in PLAN:
        target = Path(p)
        if target.exists():
            print(f"FOUND: {p} ({'dir' if target.is_dir() else 'file'})")
            if apply:
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    try: target.unlink()
                    except Exception: pass
                print(f"  -> REMOVED")
        else:
            print(f"SKIP: {p} (not found)")
    if not apply:
        print("\\n[DRY-RUN] Tidak ada perubahan. Tambahkan --apply untuk eksekusi.")

if __name__ == '__main__':
    main()
