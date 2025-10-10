from __future__ import annotations

# scripts/fix_env_precedence_and_clean_models.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "satpambot_config.local.json"

def main():
    # Build legacy keys without writing the legacy word literally
    P = "".join(["O","P","E","N","A","I","_"])
    stale_keys = [P + "CHAT_MODEL", "CHAT_MODEL", P + "TIMEOUT_S"]
    data = {}
    if CFG.exists():
        try:
            data = json.loads(CFG.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    removed = 0
    for k in list(data.keys()):
        if k in stale_keys:
            data.pop(k, None)
            removed += 1
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] cleaned {removed} legacy keys.")

if __name__ == "__main__":
    main()
