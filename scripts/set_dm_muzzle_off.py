#!/usr/bin/env python3
import json
from pathlib import Path
LOCAL = Path("local.json")
try:
    data = json.loads(LOCAL.read_text(encoding="utf-8"))
except Exception:
    data = {}
data["DM_MUZZLE"] = "off"
LOCAL.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("[OK] Set DM_MUZZLE=off in local.json (top-level).")
