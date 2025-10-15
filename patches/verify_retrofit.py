#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_retrofit.py
Cek:
- retrofit() ada di helper & scripts smoke_utils (jika ada)
- smoke_deep.py sudah pakai import prefer-helper dan memanggil retrofit(bot)
"""

import importlib.util, sys, os, re
from pathlib import Path

ROOT = Path(os.getcwd())

def _load_text(p: Path):
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return ""

def check_smoke_utils(module_path: Path, label: str):
    if not module_path.exists():
        print(f"[{label}] NOT FOUND — skip")
        return
    src = _load_text(module_path)
    ok = "def retrofit(bot):" in src
    print(f"[{label}] retrofit() {'OK' if ok else 'MISSING'} — {module_path}")

def check_smoke_deep(deep_path: Path):
    if not deep_path.exists():
        print("[deep] scripts/smoke_deep.py NOT FOUND")
        return
    src = _load_text(deep_path)
    imp_ok = "helpers import smoke_utils as smoke_utils" in src
    call_ok = "smoke_utils.retrofit(" in src
    print(f"[deep] import prefer-helper: {'OK' if imp_ok else 'NO'}")
    print(f"[deep] call retrofit(): {'OK' if call_ok else 'NO'}")

def main():
    check_smoke_utils(ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "helpers" / "smoke_utils.py", "helper")
    check_smoke_utils(ROOT / "scripts" / "smoke_utils.py", "scripts")
    check_smoke_deep(ROOT / "scripts" / "smoke_deep.py")
    print("\n[hint] Setelah patch, jalankan:  PYTHONPATH=\"$(pwd)\" python scripts/smoke_deep.py")

if __name__ == "__main__":
    main()
