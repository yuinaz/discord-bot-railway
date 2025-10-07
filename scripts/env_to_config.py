
import os, json, re, sys, pathlib
"""
Read SatpamBot.env and mirror all K=V into satpambot/config/99_env_override.json
- Keeps strings as-is. Tries to coerce integers/bools.
- Creates config dir if missing.
Usage:  py -3.10 scripts/env_to_config.py
"""
ROOT = pathlib.Path(__file__).resolve().parents[1]
env_file = ROOT / "SatpamBot.env"
cfg_dir  = ROOT / "satpambot" / "config"
out_file = cfg_dir / "99_env_override.json"
if not env_file.exists():
    print(f"[ERR] {env_file} not found"); sys.exit(1)
cfg_dir.mkdir(parents=True, exist_ok=True)
data = {}
for line in env_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"): 
        continue
    if "=" not in line: 
        continue
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip()
    # Strip optional quotes
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    # Coerce bool/int/float when sane
    lv = v.lower()
    if lv in ("true","false","yes","no","on","off"):
        v2 = lv in ("true","yes","on")
    else:
        try:
            if "." in v and all(ch.isdigit() or ch=="." or ch=="-" for ch in v):
                v2 = float(v)
            elif v.isdigit() or (v.startswith("-") and v[1:].isdigit()):
                v2 = int(v)
            else:
                v2 = v
        except Exception:
            v2 = v
    data[k] = v2
# Always include OWNER_USER_ID if present shorthand OWNER or OWNER_ID etc.
for alias in ("OWNER", "OWNER_ID", "OWNER_USER_ID"):
    if alias in data:
        data["OWNER_USER_ID"] = str(data[alias])
        break
out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] wrote {out_file} with {len(data)} keys")
