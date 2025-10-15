#!/usr/bin/env python3
"""
Repair local.json numeric fields that were accidentally saved as strings with trailing commas or spaces, e.g. "30," -> 30.
Usage:
  python scripts/repair_local_json_numbers.py
"""
import json, re, sys, os
PATH = "local.json"
RAW = open(PATH, "r", encoding="utf-8").read()

def tolerant_load(s):
    s2 = re.sub(r"//.*?$", "", s, flags=re.M)           # strip // comments
    s2 = re.sub(r"/\*.*?\*/", "", s2, flags=re.S)        # strip /* ... */ comments
    # Fix a few common structural issues (safe-ish):
    s2 = re.sub(r'(\})\s*\n\s*"', r'\1,\n"', s2)         # missing comma after }
    s2 = re.sub(r'(\])\s*\n\s*"', r'\1,\n"', s2)         # missing comma after ]
    s2 = re.sub(r",\s*([}\]])", r"\1", s2)               # trailing commas
    return json.loads(s2)

data = tolerant_load(RAW)

# Keys we expect to be numeric (int/float)
NUM_KEYS = [
  "XP_WINDOW_SEC","XP_CAP_PER_WINDOW","MIN_DELTA_ITEMS",
  "XP_PER_ITEM_TEXT","XP_PER_ITEM_SLANG","XP_PER_ITEM_PHISH",
  "BURST_MULTIPLIER","BURST_DURATION_SEC",
  "MINER_TEXT_START_DELAY_SEC","MINER_TEXT_PERIOD_SEC",
  "MINER_PHISH_START_DELAY_SEC","MINER_PHISH_PERIOD_SEC",
  "MINER_SLANG_START_DELAY_SEC","MINER_SLANG_PERIOD_SEC"
]

changed = {}
for k in NUM_KEYS:
    if k not in data: continue
    v = data[k]
    if isinstance(v, (int,float)): continue
    if isinstance(v, str):
        s = v.strip()
        s = s.rstrip(",")  # drop trailing comma
        # try int then float
        try:
            nv = int(s)
        except Exception:
            try:
                nv = float(s)
            except Exception:
                continue
        data[k] = nv
        changed[k] = (v, nv)

if changed:
    bak = PATH + ".bak"
    with open(bak, "w", encoding="utf-8") as f: f.write(RAW)
    with open(PATH, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    print("[OK] normalized numeric fields:", ", ".join(sorted(changed.keys())))
    print("Backup saved to:", bak)
else:
    print("[OK] nothing to change.")

print("Tip: you can also run -> python -m scripts.merge_local_json /path/to/fix_numeric_trailing_patch.json")
