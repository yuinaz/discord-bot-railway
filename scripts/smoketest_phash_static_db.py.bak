from __future__ import annotations

import json
import pathlib

p = pathlib.Path("data/phash_static/SATPAMBOT_PHASH_DB_V1.json")
js = json.loads(p.read_text(encoding="utf-8"))
ph = js.get("phash") or []
print(f"[OK] pHash total={len(ph)}, unique={len(set(ph))}.")
