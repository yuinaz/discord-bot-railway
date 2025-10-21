#!/usr/bin/env python3
"""
scripts/set_dm_muzzle_off.py
- Ensures top-level DM_MUZZLE is set to "off" in local.json
- (Nested dm_muzzle.mode is ignored by the runtime config loader for DM_MUZZLE lookups.)
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local.json"
data = {}
try:
    data = json.loads(LOCAL.read_text(encoding="utf-8"))
except Exception:
    data = {}

data["DM_MUZZLE"] = "off"
LOCAL.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("[OK] Set DM_MUZZLE=off in local.json (top-level).")
