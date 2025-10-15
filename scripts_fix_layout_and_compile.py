
"""
scripts_fix_layout_and_compile.py
- Hapus duplikasi layout yang bikin compile error pada smoketest (root-level 'bot/' dan 'modules/')
- Bersihkan cache/artefak
- Jalankan compileall khusus folder 'satpambot' saja
"""

import os, shutil, compileall, sys
from pathlib import Path

ROOT = Path(".").resolve()

def rm_tree(p: Path):
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
        print(f"[DEL] {p}")

def rm_glob(patterns):
    for pat in patterns:
        for p in ROOT.glob(pat):
            try:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                    print(f"[DEL] {p}")
                else:
                    p.unlink(missing_ok=True)
                    print(f"[DEL] {p}")
            except Exception as e:
                print(f"[WARN] gagal hapus {p}: {e}")

def main():
    # 1) Hapus duplicate legacy layout di root: 'bot/' & 'modules/'
    rm_tree(ROOT / "bot")
    rm_tree(ROOT / "modules")

    # 2) Bersihkan cache/artefak umum
    rm_glob(["**/__pycache__", "**/.pytest_cache", "**/.mypy_cache", "**/.ruff_cache"])
    rm_glob(["**/*.pyc", "**/*.pyo", "**/*.pyd", "**/*.orig", "**/*.rej", "**/*~"])

    # 3) Kompilasi hanya 'satpambot' supaya error compile dari duplikat tidak mengganggu
    satpam = ROOT / "satpambot"
    if not satpam.exists():
        print("[ERR] folder 'satpambot' tidak ditemukan di", ROOT)
        sys.exit(2)

    print("[INFO] compileall: satpambot/...")
    ok = compileall.compile_dir(str(satpam), maxlevels=20, quiet=1)
    if not ok:
        print("[WARN] compileall melaporkan masalah")
        sys.exit(1)
    print("[OK] compile satpambot sukses")

if __name__ == "__main__":
    main()
