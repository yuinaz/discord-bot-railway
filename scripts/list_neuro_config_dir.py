
import os, sys, glob, json

base = os.getenv("NEURO_CONFIG_DIR", "data/neuro-lite/config")
print("[neuro-config] base dir:", base, "exists:", os.path.exists(base))
if not os.path.exists(base):
    sys.exit(0)

files = sorted(glob.glob(os.path.join(base, "*.*json*")))
if not files:
    print("[neuro-config] no json files found")
else:
    for p in files:
        try:
            sz = os.path.getsize(p)
        except Exception:
            sz = -1
        print(f"- {p} ({sz} bytes)")
