import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = ROOT / "data"
wl_txt = data / "whitelist.txt"
wl_json = data / "url_whitelist.json"
bl_legacy = data / "phish_url_blocklist.json"
bl_json = data / "url_blocklist.json"

allow = []
if wl_txt.exists():
    for line in wl_txt.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        allow.append(s)
wl_json.write_text(json.dumps({"allow": sorted(set(allow))}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] wrote {wl_json} ({len(set(allow))} domains)")

domains = []
if bl_legacy.exists():
    try:
        obj = json.loads(bl_legacy.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and "domains" in obj:
            domains = obj["domains"]
        elif isinstance(obj, list):
            domains = obj
    except Exception:
        pass
bl_json.write_text(json.dumps({"domains": sorted(set(domains))}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] wrote {bl_json} ({len(set(domains))} domains)")
print("Done. Commit both JSON files so they persist across deploys.")
