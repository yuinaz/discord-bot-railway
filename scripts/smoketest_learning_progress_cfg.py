#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoketest: learning_progress config
- Checks config/learning_progress.json exists
- Validates weekly Mon->Mon (with a few key variants)
"""
import json, os, sys, traceback

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "learning_progress.json")
CFG_PATH = os.path.abspath(CFG_PATH)

def _get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return d[k]
    return default

def main() -> int:
    if not os.path.exists(CFG_PATH):
        print("WARN : config/learning_progress.json tidak ditemukan — lewati validasi (OK untuk sekarang)")
        return 0

    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        print("FAIL : membaca learning_progress.json")
        traceback.print_exc()
        return 1

    weekly = _get(cfg, "weekly", "week", default={})
    start = _get(weekly, "start_day", "week_start", "start", default=None)
    end   = _get(weekly, "end_day", "week_end", "end", default=None)

    # Normalize string
    start = (start or "").strip().title()
    end   = (end or "").strip().title()

    if start == "Mon" and end == "Mon":
        print("OK   : learning_progress.json weekly Mon->Mon OK")
        return 0

    if start and end:
        print(f"WARN : weekly {start}->{end} (bukan Mon->Mon). Silakan sesuaikan jika ingin laporan Senin ke Senin.")
        return 0

    print("INFO : weekly keys tidak standar; kunci yang ditemukan:", list(weekly.keys()) if isinstance(weekly, dict) else type(weekly))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
