import json, os, sys, pathlib
p = pathlib.Path("data/learn_progress_junior.json")
if not p.exists():
    print("[WARN] data/learn_progress_junior.json not found")
    sys.exit(0)
try:
    j = json.loads(p.read_text(encoding="utf-8"))
    assert "TK" in j and "SD" in j, "bad schema"
    print("[OK] memory JSON schema looks fine")
except Exception as e:
    print("[FAIL]", e)
