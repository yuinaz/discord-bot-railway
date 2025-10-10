from __future__ import annotations

# scripts/verify_no_vendor_final.py
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
targets = [ROOT / "satpambot", ROOT / "scripts"]

bad = []
V = "".join(["O","P","E","N","A","I"])
g = "".join(["g","p","t","-"])
p = re.compile("(" + V + r"|"+ g + ")", re.I)

ignore_names = {
    "verify_no_vendor_final.py",
    "final_vendor_purge_apply.py",
    "scrub_vendor_leftovers.py",
}

for t in targets:
    for path in t.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".py",".json",".yaml",".yml",".env",".ini",".toml"):
            if path.name in ignore_names:
                continue
            try:
                s = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if p.search(s):
                bad.append(str(path))

if bad:
    print("Remaining refs:")
    for b in bad:
        print(" -", b)
    sys.exit(1)
else:
    print("OK: no legacy-vendor or old model-name literals left in satpambot/ and scripts/.")
